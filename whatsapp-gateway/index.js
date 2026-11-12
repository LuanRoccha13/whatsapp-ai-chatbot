const { default: makeWASocket, useMultiFileAuthState, DisconnectReason } = require('@whiskeysockets/baileys');
const pino = require('pino');
const express = require('express');
const qrcodeTerminal = require('qrcode-terminal');
const QRCode = require('qrcode');
const axios = require('axios');
const path = require('path');
const fs = require('fs');

const app = express();
app.use(express.json());

const PORT = 3000;
const FASTAPI_WEBHOOK_URL = 'http://127.0.0.1:8000/webhook';

let currentQR = null;
let connectionStatus = 'initializing';
let sock = null;

async function startWhatsApp() {
    const authFolder = path.join(__dirname, 'auth_info_baileys');
    const { state, saveCreds } = await useMultiFileAuthState(authFolder);

    sock = makeWASocket({
        auth: state,
        logger: pino({ level: 'silent' }),
        printQRInTerminal: false,
        browser: ['WhatsApp AI Bot', 'Chrome', '1.0.0']
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            currentQR = qr;
            connectionStatus = 'qr_ready';
            console.log('\n======================================================');
            console.log('📲 NOVO QR CODE GERADO! ESCANEIE COM SEU WHATSAPP:');
            console.log('Ou abra no navegador: http://localhost:3000/qr');
            console.log('======================================================\n');
            qrcodeTerminal.generate(qr, { small: true });
        }

        if (connection === 'close') {
            const shouldReconnect = (lastDisconnect?.error)?.output?.statusCode !== DisconnectReason.loggedOut;
            console.log(`❌ Conexão fechada. Reconectando: ${shouldReconnect}`);
            connectionStatus = 'disconnected';
            currentQR = null;
            if (shouldReconnect) {
                setTimeout(startWhatsApp, 3000);
            }
        } else if (connection === 'open') {
            console.log('\n======================================================');
            console.log('✅ WHATSAPP CONECTADO COM SUCESSO!');
            console.log('O Bot já está ouvindo e respondendo mensagens em tempo real.');
            console.log('======================================================\n');
            connectionStatus = 'connected';
            currentQR = null;
        }
    });

    // Evento de recebimento de mensagens
    sock.ev.on('messages.upsert', async ({ messages, type }) => {
        if (type !== 'notify') return;

        for (const msg of messages) {
            // Ignora mensagens do próprio bot ou sem conteúdo
            if (msg.key.fromMe) continue;
            if (!msg.message) continue;

            const remoteJid = msg.key.remoteJid || '';
            const isGroup = remoteJid.endsWith('@g.us');
            const isNewsletter = remoteJid.endsWith('@newsletter');
            const isBroadcast = remoteJid.includes('broadcast');
            
            // Ignora grupos, canais/newsletters e status/broadcasts
            if (isGroup || isNewsletter || isBroadcast) continue;

            const senderPhone = remoteJid.replace('@s.whatsapp.net', '');
            const senderName = msg.pushName || 'Cliente';

            // Extrai texto da mensagem
            const messageText = 
                msg.message.conversation ||
                msg.message.extendedTextMessage?.text ||
                msg.message.imageMessage?.caption ||
                '';

            if (!messageText.trim()) continue;

            console.log(`📩 Mensagem recebida de [${senderName} - ${senderPhone}]: "${messageText}"`);

            // Encaminha para o backend FastAPI processar com a IA
            try {
                await axios.post(FASTAPI_WEBHOOK_URL, {
                    sender_phone: senderPhone,
                    sender_name: senderName,
                    message_text: messageText,
                    is_group: false
                }, { timeout: 10000 });
            } catch (err) {
                console.error(`Erro ao encaminhar para o webhook FastAPI: ${err.message}`);
            }
        }
    });
}

// Endpoint para envio de mensagem de volta ao WhatsApp
app.post('/send-message', async (req, res) => {
    const { number, text } = req.body;

    if (!number || !text) {
        return res.status(400).json({ error: 'Campos number e text são obrigatórios.' });
    }

    if (connectionStatus !== 'connected' || !sock) {
        return res.status(503).json({ error: 'WhatsApp ainda não está conectado.' });
    }

    try {
        const cleanNumber = number.replace(/\D/g, '');
        const jid = `${cleanNumber}@s.whatsapp.net`;

        // Simula "digitando..." por 1.5s
        await sock.sendPresenceUpdate('composing', jid);
        await new Promise(r => setTimeout(r, 1200));

        await sock.sendMessage(jid, { text: text });
        console.log(`📤 Resposta enviada com sucesso para ${cleanNumber}: "${text.substring(0, 60)}..."`);
        return res.json({ status: 'sent', number: cleanNumber });
    } catch (err) {
        console.error(`Erro ao enviar mensagem: ${err.message}`);
        return res.status(500).json({ error: err.message });
    }
});

// Endpoint de status
app.get('/', (req, res) => {
    res.json({
        service: 'WhatsApp Gateway Baileys',
        status: connectionStatus,
        qr_page: 'http://localhost:3000/qr'
    });
});

// Página web para visualização amigável do QR Code
app.get('/qr', async (req, res) => {
    if (connectionStatus === 'connected') {
        return res.send(`
            <!DOCTYPE html>
            <html lang="pt-br">
            <head><meta charset="UTF-8"><title>WhatsApp Conectado</title>
            <style>body{font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;background:#111b21;color:#e9edef;text-align:center;}</style>
            </head>
            <body>
                <div>
                    <h1 style="color:#00a884;">✅ WhatsApp Conectado com Sucesso!</h1>
                    <p>O Bot já está ativo e pronto para responder no seu número.</p>
                </div>
            </body>
            </html>
        `);
    }

    if (!currentQR) {
        return res.send(`
            <!DOCTYPE html>
            <html lang="pt-br">
            <head><meta charset="UTF-8"><title>Aguardando QR Code</title>
            <meta http-equiv="refresh" content="2">
            <style>body{font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;background:#111b21;color:#e9edef;text-align:center;}</style>
            </head>
            <body>
                <div>
                    <h2>⏳ Gerando QR Code...</h2>
                    <p>Aguarde um momento, a página recarregará automaticamente.</p>
                </div>
            </body>
            </html>
        `);
    }

    try {
        const qrImage = await QRCode.toDataURL(currentQR, { width: 320 });
        res.send(`
            <!DOCTYPE html>
            <html lang="pt-br">
            <head>
                <meta charset="UTF-8">
                <title>Conectar WhatsApp</title>
                <meta http-equiv="refresh" content="15">
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; background: #111b21; color: #e9edef; margin: 0; }
                    .card { background: #202c33; padding: 30px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.4); text-align: center; max-width: 400px; }
                    h2 { color: #00a884; margin-top: 0; }
                    ol { text-align: left; line-height: 1.6; font-size: 14px; color: #8696a0; }
                    img { border-radius: 8px; border: 4px solid #fff; margin: 15px 0; }
                </style>
            </head>
            <body>
                <div class="card">
                    <h2>📲 Conectar WhatsApp</h2>
                    <ol>
                        <li>Abra o WhatsApp no seu celular</li>
                        <li>Toque em <b>Menu</b> (Android) ou <b>Configurações</b> (iPhone)</li>
                        <li>Selecione <b>Aparelhos conectados</b></li>
                        <li>Toque em <b>Conectar aparelho</b> e aponte para o QR Code abaixo</li>
                    </ol>
                    <img src="${qrImage}" alt="QR Code WhatsApp" />
                    <p style="font-size: 12px; color: #8696a0;">Atualiza automaticamente a cada 15 segundos</p>
                </div>
            </body>
            </html>
        `);
    } catch (e) {
        res.status(500).send("Erro ao gerar imagem do QR Code: " + e.message);
    }
});

app.listen(PORT, () => {
    console.log(`WhatsApp Gateway iniciado na porta ${PORT}`);
    startWhatsApp();
});
