
import discord
from discord.ext import commands
import asyncio
import json
from datetime import datetime
import os

# Bot設定
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# メッセージログを保存するための辞書
message_logs = {}

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')

@bot.event
async def on_message(message):
    # ボット自身のメッセージは無視
    if message.author.bot:
        return
    
    # メッセージログを記録
    guild_id = str(message.guild.id) if message.guild else "DM"
    channel_id = str(message.channel.id)
    
    if guild_id not in message_logs:
        message_logs[guild_id] = {}
    if channel_id not in message_logs[guild_id]:
        message_logs[guild_id][channel_id] = []
    
    # メッセージデータを保存
    message_data = {
        "author": {
            "name": message.author.display_name,
            "id": str(message.author.id),
            "avatar_url": str(message.author.display_avatar.url)
        },
        "content": message.content,
        "timestamp": message.created_at.isoformat(),
        "channel": message.channel.name if hasattr(message.channel, 'name') else 'DM',
        "attachments": [att.url for att in message.attachments]
    }
    
    message_logs[guild_id][channel_id].append(message_data)
    
    # 最新100件のみ保持
    if len(message_logs[guild_id][channel_id]) > 100:
        message_logs[guild_id][channel_id] = message_logs[guild_id][channel_id][-100:]
    
    await bot.process_commands(message)

@bot.command(name='log')
async def show_log(ctx, limit: int = 10):
    """チャンネルのメッセージログを表示"""
    guild_id = str(ctx.guild.id)
    channel_id = str(ctx.channel.id)
    
    if guild_id not in message_logs or channel_id not in message_logs[guild_id]:
        await ctx.send("このチャンネルにはログがありません。")
        return
    
    logs = message_logs[guild_id][channel_id][-limit:]
    
    embed = discord.Embed(
        title=f"#{ctx.channel.name} のメッセージログ",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    
    for log in logs:
        timestamp = datetime.fromisoformat(log['timestamp']).strftime('%m/%d %H:%M')
        content = log['content'][:50] + "..." if len(log['content']) > 50 else log['content']
        
        embed.add_field(
            name=f"{log['author']['name']} ({timestamp})",
            value=content if content else "*添付ファイルのみ*",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name='masquerade')
async def masquerade_message(ctx, user_id: int, *, message_content):
    """指定したユーザーになりすましてメッセージを送信"""
    try:
        # ユーザー情報を取得
        user = bot.get_user(user_id) or await bot.fetch_user(user_id)
        if not user:
            await ctx.send("ユーザーが見つかりません。")
            return
        
        # Webhookを作成または取得
        webhooks = await ctx.channel.webhooks()
        webhook = None
        
        for wh in webhooks:
            if wh.name == "MasqueradeBot":
                webhook = wh
                break
        
        if not webhook:
            webhook = await ctx.channel.create_webhook(name="MasqueradeBot")
        
        # 元のメッセージを削除
        try:
            await ctx.message.delete()
        except:
            pass
        
        # ユーザーになりすましてメッセージを送信
        await webhook.send(
            content=message_content,
            username=user.display_name,
            avatar_url=str(user.display_avatar.url)
        )
        
    except Exception as e:
        await ctx.send(f"エラーが発生しました: {str(e)}")

@bot.command(name='copy_message')
async def copy_message(ctx, message_id: int):
    """指定したメッセージをマスカレードで複製"""
    try:
        # メッセージを取得
        message = await ctx.channel.fetch_message(message_id)
        
        # Webhookを作成または取得
        webhooks = await ctx.channel.webhooks()
        webhook = None
        
        for wh in webhooks:
            if wh.name == "MasqueradeBot":
                webhook = wh
                break
        
        if not webhook:
            webhook = await ctx.channel.create_webhook(name="MasqueradeBot")
        
        # 元のコマンドメッセージを削除
        try:
            await ctx.message.delete()
        except:
            pass
        
        # 複製メッセージを送信
        content = message.content
        if message.attachments:
            content += "\n\n**添付ファイル:**\n"
            for att in message.attachments:
                content += f"📎 {att.filename}\n"
        
        await webhook.send(
            content=content,
            username=message.author.display_name,
            avatar_url=str(message.author.display_avatar.url)
        )
        
        # 元のメッセージ情報を追加
        info_embed = discord.Embed(
            title="Original Message Info",
            description=f"Original: {message.channel.mention} • {message.created_at.strftime('%Y/%m/%d %H:%M')}",
            color=0x808080
        )
        
        await webhook.send(embed=info_embed, username="System", avatar_url=bot.user.display_avatar.url)
        
    except Exception as e:
        await ctx.send(f"エラーが発生しました: {str(e)}")

@bot.command(name='clear_logs')
async def clear_logs(ctx):
    """このチャンネルのログをクリア"""
    guild_id = str(ctx.guild.id)
    channel_id = str(ctx.channel.id)
    
    if guild_id in message_logs and channel_id in message_logs[guild_id]:
        message_logs[guild_id][channel_id] = []
        await ctx.send("ログをクリアしました。")
    else:
        await ctx.send("クリアするログがありません。")

@bot.command(name='all_message_log')
async def copy_all_messages(ctx, server_id: int, limit: int = 50):
    """指定したサーバーのすべてのチャンネルからメッセージをコピー（最高速）"""
    try:
        # サーバーを取得
        guild = bot.get_guild(server_id)
        if not guild:
            await ctx.send("指定されたサーバーが見つかりません。")
            return
        
        # Webhookを作成または取得
        webhooks = await ctx.channel.webhooks()
        webhook = None
        
        for wh in webhooks:
            if wh.name == "MasqueradeBot":
                webhook = wh
                break
        
        if not webhook:
            webhook = await ctx.channel.create_webhook(name="MasqueradeBot")
        
        # 元のコマンドメッセージを削除
        try:
            await ctx.message.delete()
        except:
            pass
        
        # 並行処理でチャンネルを処理
        async def process_channel(channel):
            messages_sent = 0
            try:
                # メッセージリストを先に収集
                messages = []
                async for message in channel.history(limit=limit, oldest_first=True):
                    messages.append(message)
                
                # 並行でメッセージを送信
                send_tasks = []
                for message in messages:
                    content = message.content
                    
                    # 添付ファイルがある場合
                    if message.attachments:
                        if content:
                            content += "\n\n"
                        content += "**添付ファイル:**\n"
                        for att in message.attachments:
                            content += f"📎 {att.filename}\n"
                    
                    # 埋め込みがある場合
                    embeds = message.embeds if message.embeds else None
                    
                    # 並行送信タスクを作成
                    task = webhook.send(
                        content=content if content else "*メッセージなし*",
                        username=message.author.display_name,
                        avatar_url=str(message.author.display_avatar.url),
                        embeds=embeds
                    )
                    send_tasks.append(task)
                
                # すべてのメッセージを並行送信
                await asyncio.gather(*send_tasks, return_exceptions=True)
                messages_sent = len(messages)
                
                # チャンネル情報を送信
                info_embed = discord.Embed(
                    title="Channel Info",
                    description=f"Original: {guild.name} #{channel.name} ({messages_sent} messages)",
                    color=0x808080,
                    timestamp=datetime.now()
                )
                
                await webhook.send(
                    embed=info_embed,
                    username="System",
                    avatar_url=bot.user.display_avatar.url
                )
                
                return messages_sent
                
            except discord.Forbidden:
                return 0
            except Exception as e:
                print(f"Error copying from channel {channel.name}: {str(e)}")
                return 0
        
        # 全チャンネルを並行処理
        channel_tasks = []
        for channel in guild.text_channels:
            task = process_channel(channel)
            channel_tasks.append(task)
        
        # すべてのチャンネルを並行処理
        results = await asyncio.gather(*channel_tasks, return_exceptions=True)
        
        # 合計コピー数を計算
        copied_count = sum(result for result in results if isinstance(result, int))
        
        # 完了メッセージ
        completion_embed = discord.Embed(
            title="コピー完了（最高速モード）",
            description=f"サーバー: {guild.name}\nコピーしたメッセージ数: {copied_count}\n処理チャンネル数: {len(guild.text_channels)}",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        
        await webhook.send(
            embed=completion_embed,
            username="System",
            avatar_url=bot.user.display_avatar.url
        )
        
    except Exception as e:
        await ctx.send(f"エラーが発生しました: {str(e)}")

@bot.command(name='help_masquerade')
async def help_masquerade(ctx):
    """ボットの使い方を表示"""
    embed = discord.Embed(
        title="マスカレードBot ヘルプ",
        color=0x0099ff
    )
    
    embed.add_field(
        name="!log [件数]",
        value="チャンネルのメッセージログを表示（デフォルト10件）",
        inline=False
    )
    
    embed.add_field(
        name="!masquerade <ユーザーID> <メッセージ>",
        value="指定したユーザーになりすましてメッセージを送信",
        inline=False
    )
    
    embed.add_field(
        name="!copy_message <メッセージID>",
        value="指定したメッセージをマスカレードで複製",
        inline=False
    )
    
    embed.add_field(
        name="!all_message_log <サーバーID> [件数]",
        value="指定したサーバーのすべてのチャンネルからメッセージをコピー（デフォルト50件）",
        inline=False
    )
    
    embed.add_field(
        name="!clear_logs",
        value="このチャンネルのログをクリア",
        inline=False
    )
    
    await ctx.send(embed=embed)

# Render用のWebサーバーを追加
from threading import Thread
import time

def keep_alive():
    """Render用のキープアライブ機能"""
    import http.server
    import socketserver
    
    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Discord Bot is running on Render!')
        
        def log_message(self, format, *args):
            # ログを抑制
            return
    
    port = int(os.environ.get('PORT', 10000))
    with socketserver.TCPServer(("0.0.0.0", port), Handler) as httpd:
        print(f"Keep-alive server running on port {port}")
        httpd.serve_forever()

# Botの実行
if __name__ == "__main__":
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("DISCORD_BOT_TOKEN環境変数を設定してください。")
        print("Render環境変数でトークンを設定してください。")
    else:
        # キープアライブサーバーをバックグラウンドで開始
        keep_alive_thread = Thread(target=keep_alive, daemon=True)
        keep_alive_thread.start()
        
        print("Discord Bot starting on Render...")
        bot.run(token)
