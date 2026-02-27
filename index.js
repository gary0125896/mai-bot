const { Client, Events, GatewayIntentBits, REST, Routes, SlashCommandBuilder } = require('discord.js');
const { spawn } = require('child_process');
const { token, clientId, guildId } = require('./config.json');

const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent,
        GatewayIntentBits.GuildMembers,
    ]
});

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

    // --- 關鍵修正：確保 DeferReply 是第一順位執行，且完全捕捉錯誤 ---
    let deferred = false;
    try {
        await interaction.deferReply();
        deferred = true;
    } catch (err) {
        console.error("❌ DeferReply 失敗，互動已過期 (超過 3 秒):", err.message);
        return; // 直接中斷，避免執行後續 spawn 浪費效能
    }

    const { commandName } = interaction;

    // --- 指令 A: b50 ---
    if (commandName === 'b50') {
        const TARGET_FRIEND_ID = interaction.options.getString('userid');

        const pythonProcess = spawn('python', ['catch-friend-score.py', TARGET_FRIEND_ID], {
            env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
        });

        let resultData = "";

        pythonProcess.stdout.on('data', (data) => {
            const output = data.toString();
            resultData += output;
            const lines = output.split('\n').filter(l => l.trim().length > 0);
            lines.forEach((line) => {
                if (!line.includes("OUTPUT_FILE:")) {
                    // 使用 catch 靜默處理過期回應
                    interaction.editReply(`⏳ **正在分析**：${line.trim()}`).catch(() => {});
                }
            });
        });

        pythonProcess.on('close', async (code) => {
            if (!deferred) return;
            try {
                if (code === 0) {
                    const fileMatch = resultData.match(/OUTPUT_FILE:(.+)/);
                    if (fileMatch && fileMatch[1].trim() !== "ERROR_PATH") {
                        await interaction.editReply({
                            content: `✅ **${TARGET_FRIEND_ID}** 的 B50 分析完成！`,
                            files: [fileMatch[1].trim()]
                        });
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

        const addProcess = spawn('python', ['add_friend.py', FRIEND_CODE], {
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