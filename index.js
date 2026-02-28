const fs = require('fs'); // 加上這行，才能使用刪除功能
const { Client, Events, GatewayIntentBits, REST, Routes, SlashCommandBuilder } = require('discord.js');
const { spawn } = require('child_process');
require('dotenv').config();

const token = process.env.MAI_BOT_TOKEN;
const clientId = process.env.CLIENT_ID;
const guildId = process.env.GUILD_ID;

const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent,
        GatewayIntentBits.GuildMembers,
    ]
});

// --- 全域鎖變數 ---
let isProcessing = false;

const commands = [
    new SlashCommandBuilder()
        .setName('b50')
        .setDescription('查詢 B50 資料')
        .addStringOption(option =>
            option.setName('userid').setDescription('請輸入你的玩家ID').setRequired(true)
        ),
    new SlashCommandBuilder()
        .setName('addfriend')
        .setDescription('讓機器人主動加你好友')
        .addStringOption(option =>
            option.setName('friendcode').setDescription('請輸入你的好友代碼 (Friend Code)').setRequired(true)
        )
].map(command => command.toJSON());

const rest = new REST({ version: '10' }).setToken(token);

client.once(Events.ClientReady, async (readyClient) => {
    console.log(`✅ Ready! Logged in as ${readyClient.user.tag}`);
    try {
        await rest.put(Routes.applicationGuildCommands(clientId, guildId), { body: commands });
        console.log('成功註冊指令：/b50, /addfriend');
    } catch (error) {
        console.error('註冊指令失敗:', error);
    }
});

client.on(Events.InteractionCreate, async (interaction) => {
    if (!interaction.isChatInputCommand()) return;

    // --- 檢查全域鎖 ---
    if (isProcessing) {
        return interaction.reply({ content: "⚠️ 機器人正在處理另一個請求中，請稍候 30-60 秒再試。", ephemeral: true });
    }

    let deferred = false;
    try {
        await interaction.deferReply();
        deferred = true;
    } catch (err) {
        console.error("❌ DeferReply 失敗，互動已過期 (超過 3 秒):", err.message);
        return;
    }

    const { commandName } = interaction;
    
    // 進入指令邏輯，上鎖
    isProcessing = true;

    // --- 指令 A: b50 ---
    if (commandName === 'b50') {
        const TARGET_FRIEND_ID = interaction.options.getString('userid');

        const pythonProcess = spawn('python3', ['catch-friend-score.py', TARGET_FRIEND_ID], {
            env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
        });

        let resultData = "";

        pythonProcess.stdout.on('data', (data) => {
            const output = data.toString();
            resultData += output;
            const lines = output.split('\n').filter(l => l.trim().length > 0);
            lines.forEach((line) => {
                if (!line.includes("OUTPUT_FILE:")) {
                    interaction.editReply(`⏳ **正在分析**：${line.trim()}`).catch(() => {});
                }
            });
        });

        pythonProcess.on('close', async (code) => {
            isProcessing = false; // 程序結束，解鎖
            if (!deferred) return;
            try {
                if (code === 0) {
                    const fileMatch = resultData.match(/OUTPUT_FILE:(.+)/);
                    if (fileMatch && fileMatch[1].trim() !== "ERROR_PATH") {
                        const filePath = fileMatch[1].trim();

                        // 1. 先上傳到 Discord
                        await interaction.editReply({
                            content: `✅ **${TARGET_FRIEND_ID}** 的 B50 分析完成！`,
                            files: [filePath]
                        });

                        // 2. 上傳完畢後立刻刪除檔案
                        if (fs.existsSync(filePath)) {
                            fs.unlinkSync(filePath);
                            console.log(`🗑️ 已刪除暫存圖檔: ${filePath}`);
                        }
                    } else {
                        await interaction.editReply(`❌ 分析完成，但找不到數據。請確認是否已加好友。`);
                    }
                } else {
                    await interaction.editReply(`❌ 查詢失敗或系統錯誤 (Code ${code})`);
                }
            } catch (e) { console.error("B50 回應失敗:", e.message); }
        });
    }

    // --- 指令 B: addfriend ---
    if (commandName === 'addfriend') {
        const FRIEND_CODE = interaction.options.getString('friendcode');

        const addProcess = spawn('python3', ['add_friend.py', FRIEND_CODE], {
            env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
        });

        let addResult = "";

        addProcess.stdout.on('data', (data) => {
            const output = data.toString();
            addResult += output;
            const currentStatus = output.split('\n').filter(l => l.trim()).pop();
            if (currentStatus) {
                interaction.editReply(`🤖 **加好友進度**：${currentStatus}`).catch(() => {});
            }
        });

        addProcess.on('close', async (code) => {
            isProcessing = false; // 程序結束，解鎖
            if (!deferred) return;
            try {
                if (addResult.includes("SUCCESS_REQUEST_SENT")) {
                    await interaction.editReply(`✅ **申請成功**！機器人已向 \`${FRIEND_CODE}\` 送出好友邀請。`);
                } else if (addResult.includes("ERROR_WRONG_CODE")) {
                    await interaction.editReply(`❌ **申請失敗**：好友代碼錯誤。`);
                } else if (addResult.includes("ERROR_ALREADY_FRIEND_OR_FULL")) {
                    await interaction.editReply(`⚠️ **提示**：無法送出申請。可能已是好友或列表已滿。`);
                } else {
                    await interaction.editReply(`❌ **申請發生錯誤** (Code: ${code})。`);
                }
            } catch (e) { console.error("AddFriend 回應失敗:", e.message); }
        });
    }
});

client.on('error', console.error);
client.login(token);