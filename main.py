import discord
from discord.ext import commands
import asyncio
import os
from datetime import datetime, timedelta
from flask import Flask, jsonify # Flaskを追加

# Flaskアプリのインスタンスを作成
app = Flask(__name__)

# Bot setup with all intents
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')

# 新しいエンドポイントを追加（Renderのヘルスチェック用）
@app.route('/')
def home():
    return "Bot is running!"

@app.route('/health')
def health_check():
    # ボットがログインしているかどうかの簡易チェック
    if bot.is_ready():
        return jsonify(status="healthy", bot_user=str(bot.user))
    else:
        return jsonify(status="unhealthy", message="Bot not ready"), 503


@bot.command(name='serverlogs')
@commands.has_permissions(view_audit_log=True)
async def get_server_logs(ctx, log_type: str = 'all', limit: int = 10):
    """
    サーバーログを取得する
    使用法: /serverlogs [log_type] [limit]
    log_type: all, join, leave, ban, kick, delete, edit
    limit: 取得するログの数 (最大50)
    """
    if limit > 50:
        limit = 50
    
    guild = ctx.guild
    
    try:
        if log_type.lower() == 'all' or log_type.lower() == 'audit':
            # 監査ログを取得
            embed = discord.Embed(title=f"{guild.name} - 監査ログ", color=0x00ff00)
            
            async for entry in guild.audit_logs(limit=limit):
                timestamp = entry.created_at.strftime("%Y-%m-%d %H:%M:%S")
                action = entry.action.name
                user = entry.user.display_name if entry.user else "不明"
                target = getattr(entry.target, 'display_name', str(entry.target)) if entry.target else "不明"
                
                embed.add_field(
                    name=f"{action} - {timestamp}",
                    value=f"実行者: {user}\n対象: {target}",
                    inline=False
                )
            
            await ctx.send(embed=embed)
        
        elif log_type.lower() == 'join':
            # 参加ログ
            embed = discord.Embed(title=f"{guild.name} - 参加ログ", color=0x00ff00)
            
            async for entry in guild.audit_logs(action=discord.AuditLogAction.member_update, limit=limit):
                if entry.target:
                    timestamp = entry.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    embed.add_field(
                        name=f"メンバー参加 - {timestamp}",
                        value=f"ユーザー: {entry.target.display_name}",
                        inline=False
                    )
            
            await ctx.send(embed=embed)
        
        elif log_type.lower() == 'ban':
            # BANログ
            embed = discord.Embed(title=f"{guild.name} - BANログ", color=0xff0000)
            
            async for entry in guild.audit_logs(action=discord.AuditLogAction.ban, limit=limit):
                timestamp = entry.created_at.strftime("%Y-%m-%d %H:%M:%S")
                user = entry.user.display_name if entry.user else "不明"
                target = entry.target.display_name if entry.target else "不明"
                reason = entry.reason or "理由なし"
                
                embed.add_field(
                    name=f"BAN - {timestamp}",
                    value=f"実行者: {user}\n対象: {target}\n理由: {reason}",
                    inline=False
                )
            
            await ctx.send(embed=embed)
        
        elif log_type.lower() == 'kick':
            # キックログ
            embed = discord.Embed(title=f"{guild.name} - キックログ", color=0xff8800)
            
            async for entry in guild.audit_logs(action=discord.AuditLogAction.kick, limit=limit):
                timestamp = entry.created_at.strftime("%Y-%m-%d %H:%M:%S")
                user = entry.user.display_name if entry.user else "不明"
                target = entry.target.display_name if entry.target else "不明"
                reason = entry.reason or "理由なし"
                
                embed.add_field(
                    name=f"キック - {timestamp}",
                    value=f"実行者: {user}\n対象: {target}\n理由: {reason}",
                    inline=False
                )
            
            await ctx.send(embed=embed)
        
        elif log_type.lower() == 'delete':
            # メッセージ削除ログ
            embed = discord.Embed(title=f"{guild.name} - メッセージ削除ログ", color=0x880000)
            
            async for entry in guild.audit_logs(action=discord.AuditLogAction.message_delete, limit=limit):
                timestamp = entry.created_at.strftime("%Y-%m-%d %H:%M:%S")
                user = entry.user.display_name if entry.user else "不明"
                target = entry.target.display_name if entry.target else "不明"
                
                embed.add_field(
                    name=f"メッセージ削除 - {timestamp}",
                    value=f"削除者: {user}\n対象ユーザー: {target}",
                    inline=False
                )
            
            await ctx.send(embed=embed)
        
        else:
            await ctx.send("無効なログタイプです。使用可能: all, join, ban, kick, delete")
    
    except discord.Forbidden:
        await ctx.send("監査ログにアクセスする権限がありません。")
    except Exception as e:
        await ctx.send(f"エラーが発生しました: {str(e)}")

@bot.command(name='masquerade')
@commands.has_permissions(manage_webhooks=True)
async def masquerade_message(ctx, member: discord.Member, *, message):
    """
    指定したメンバーになりすましてメッセージを送信
    使用法: /masquerade @ユーザー メッセージ内容
    """
    try:
        # ウェブフックを作成または取得
        webhooks = await ctx.channel.webhooks()
        webhook = None
        
        for wh in webhooks:
            if wh.name == "MasqueradeBot":
                webhook = wh
                break
        
        if not webhook:
            webhook = await ctx.channel.create_webhook(name="MasqueradeBot")
        
        # 元のメッセージを削除
        await ctx.message.delete()
        
        # なりすましメッセージを送信
        await webhook.send(
            content=message,
            username=member.display_name,
            avatar_url=member.avatar.url if member.avatar else member.default_avatar.url
        )
        
    except discord.Forbidden:
        await ctx.send("ウェブフックを管理する権限がありません。")
    except Exception as e:
        await ctx.send(f"エラーが発生しました: {str(e)}")

@bot.command(name='transfer_messages')
@commands.has_permissions(read_message_history=True, manage_webhooks=True)
async def transfer_messages(ctx, source_channel: discord.TextChannel, target_channel_id: int, limit: int = 50):
    """
    指定したチャンネルのメッセージを他のサーバーのチャンネルに転送
    使用法: /transfer_messages #ソースチャンネル ターゲットチャンネルID [limit]
    """
    if limit > 100:
        limit = 100
    
    try:
        # ターゲットチャンネルを取得
        target_channel = bot.get_channel(target_channel_id)
        if not target_channel:
            await ctx.send("ターゲットチャンネルが見つかりません。")
            return
        
        # ターゲットチャンネルのウェブフックを作成または取得
        webhooks = await target_channel.webhooks()
        webhook = None
        
        for wh in webhooks:
            if wh.name == "TransferBot":
                webhook = wh
                break
        
        if not webhook:
            webhook = await target_channel.create_webhook(name="TransferBot")
        
        # メッセージを取得して転送
        messages_transferred = 0
        async for message in source_channel.history(limit=limit, oldest_first=True):
            if message.author.bot:
                continue  # Botのメッセージはスキップ
            
            # 添付ファイルがある場合の処理
            files = []
            if message.attachments:
                for attachment in message.attachments:
                    try:
                        file_data = await attachment.read()
                        files.append(discord.File(
                            fp=discord.utils._BytesIOWrapper(file_data),
                            filename=attachment.filename
                        ))
                    except:
                        continue
            
            # マスカレードメッセージを送信
            await webhook.send(
                content=message.content or "[添付ファイル]",
                username=message.author.display_name,
                avatar_url=message.author.avatar.url if message.author.avatar else message.author.default_avatar.url,
                files=files
            )
            
            messages_transferred += 1
            await asyncio.sleep(0.5)  # レート制限を避けるため
        
        await ctx.send(f"✅ {messages_transferred}件のメッセージを転送しました。")
        
    except discord.Forbidden:
        await ctx.send("必要な権限がありません。")
    except Exception as e:
        await ctx.send(f"エラーが発生しました: {str(e)}")

@bot.command(name='clone_user_messages')
@commands.has_permissions(read_message_history=True, manage_webhooks=True)
async def clone_user_messages(ctx, user: discord.Member, source_channel: discord.TextChannel, target_channel_id: int, limit: int = 20):
    """
    特定のユーザーのメッセージのみを他のサーバーに転送
    使用法: /clone_user_messages @ユーザー #ソースチャンネル ターゲットチャンネルID [limit]
    """
    if limit > 50:
        limit = 50
    
    try:
        # ターゲットチャンネルを取得
        target_channel = bot.get_channel(target_channel_id)
        if not target_channel:
            await ctx.send("ターゲットチャンネルが見つかりません。")
            return
        
        # ターゲットチャンネルのウェブフックを作成または取得
        webhooks = await target_channel.webhooks()
        webhook = None
        
        for wh in webhooks:
            if wh.name == "CloneBot":
                webhook = wh
                break
        
        if not webhook:
            webhook = await target_channel.create_webhook(name="CloneBot")
        
        # 特定ユーザーのメッセージを取得して転送
        messages_transferred = 0
        async for message in source_channel.history(limit=limit * 5):  # より多くのメッセージから検索
            if message.author.id != user.id or message.author.bot:
                continue
            
            if messages_transferred >= limit:
                break
            
            # 添付ファイルがある場合の処理
            files = []
            if message.attachments:
                for attachment in message.attachments:
                    try:
                        file_data = await attachment.read()
                        files.append(discord.File(
                            fp=discord.utils._BytesIOWrapper(file_data),
                            filename=attachment.filename
                        ))
                    except:
                        continue
            
            # マスカレードメッセージを送信
            await webhook.send(
                content=message.content or "[添付ファイル]",
                username=user.display_name,
                avatar_url=user.avatar.url if user.avatar else user.default_avatar.url,
                files=files
            )
            
            messages_transferred += 1
            await asyncio.sleep(0.5)  # レート制限を避けるため
        
        await ctx.send(f"✅ {user.display_name}の{messages_transferred}件のメッセージを転送しました。")
        
    except discord.Forbidden:
        await ctx.send("必要な権限がありません。")
    except Exception as e:
        await ctx.send(f"エラーが発生しました: {str(e)}")

@bot.command(name='channellogs')
@commands.has_permissions(read_message_history=True)
async def get_channel_logs(ctx, channel: discord.TextChannel = None, limit: int = 10):
    """
    指定したチャンネルのメッセージログを取得
    使用法: /channellogs #チャンネル [limit]
    """
    if not channel:
        channel = ctx.channel
    
    if limit > 50:
        limit = 50
    
    embed = discord.Embed(title=f"#{channel.name} - メッセージログ", color=0x0099ff)
    
    try:
        messages = []
        async for message in channel.history(limit=limit):
            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
            content = message.content[:100] + "..." if len(message.content) > 100 else message.content
            if not content:
                content = "[添付ファイルまたは埋め込み]"
            
            messages.append(f"**{message.author.display_name}** ({timestamp})\n{content}")
        
        # メッセージを逆順にして最新から表示
        messages.reverse()
        
        for i, msg in enumerate(messages[:10]):  # 最大10件まで表示
            embed.add_field(name=f"メッセージ {i+1}", value=msg, inline=False)
        
        await ctx.send(embed=embed)
        
    except discord.Forbidden:
        await ctx.send("メッセージ履歴を読む権限がありません。")
    except Exception as e:
        await ctx.send(f"エラーが発生しました: {str(e)}")

@bot.command(name='userinfo')
async def user_info(ctx, member: discord.Member = None):
    """
    ユーザー情報を表示
    使用法: /userinfo @ユーザー
    """
    if not member:
        member = ctx.author
    
    embed = discord.Embed(title=f"{member.display_name} の情報", color=member.color)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    
    embed.add_field(name="ユーザー名", value=f"{member.name}#{member.discriminator}", inline=True)
    embed.add_field(name="ID", value=member.id, inline=True)
    embed.add_field(name="参加日", value=member.joined_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="アカウント作成日", value=member.created_at.strftime("%Y-%m-%d"), inline=True)
    
    roles = [role.name for role in member.roles[1:]]  # @everyoneロールを除外
    if roles:
        embed.add_field(name="ロール", value=", ".join(roles), inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='copy_all_channels')
@commands.has_permissions(read_message_history=True, manage_webhooks=True)
async def copy_all_channels(ctx, target_server_id: int):
    """
    サーバーのすべてのチャンネルの全メッセージを他のサーバーにコピー（最速実行）
    使用法: /copy_all_channels ターゲットサーバーID
    """
    source_guild = ctx.guild
    target_guild = bot.get_guild(target_server_id)
    
    if not target_guild:
        await ctx.send("ターゲットサーバーが見つかりません。")
        return
    
    status_msg = await ctx.send("🚀 全チャンネルの全メッセージコピーを開始します...")
    
    try:
        # 並列処理用のタスクリスト
        tasks = []
        
        for channel in source_guild.text_channels:
            # 各チャンネルのコピータスクを作成（全メッセージ）
            task = copy_channel_fast(channel, target_guild)
            tasks.append(task)
        
        # 全チャンネルを並列でコピー（レート制限無視）
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for result in results if result is True)
        total_channels = len(source_guild.text_channels)
        
        await status_msg.edit(content=f"✅ 全メッセージコピー完了: {success_count}/{total_channels} チャンネル")
        
    except Exception as e:
        await status_msg.edit(content=f"❌ エラー: {str(e)}")

async def copy_channel_fast(source_channel, target_guild):
    """
    単一チャンネルの全メッセージを高速でコピー
    """
    try:
        # ターゲットサーバーに同名チャンネルを作成または取得
        target_channel = None
        for channel in target_guild.text_channels:
            if channel.name == source_channel.name:
                target_channel = channel
                break
        
        if not target_channel:
            # チャンネルが存在しない場合は作成
            target_channel = await target_guild.create_text_channel(
                name=source_channel.name,
                topic=source_channel.topic,
                slowmode_delay=source_channel.slowmode_delay
            )
        
        # ウェブフックを作成
        webhook = await target_channel.create_webhook(name="FastCopyBot")
        
        # メッセージを取得して並列転送（制限なし = 全メッセージ）
        message_tasks = []
        messages = []
        
        async for message in source_channel.history(limit=None, oldest_first=True):
            if not message.author.bot:
                messages.append(message)
        
        # メッセージを並列で送信（レート制限無視）
        for message in messages:
            task = send_message_fast(webhook, message)
            message_tasks.append(task)
        
        # 全メッセージを並列送信
        await asyncio.gather(*message_tasks, return_exceptions=True)
        
        # 使用後はウェブフックを削除
        await webhook.delete()
        
        return True
        
    except Exception:
        return False

async def send_message_fast(webhook, message):
    """
    単一メッセージを高速送信
    """
    try:
        # 添付ファイルの処理
        files = []
        if message.attachments:
            for attachment in message.attachments:
                try:
                    file_data = await attachment.read()
                    files.append(discord.File(
                        fp=discord.utils._BytesIOWrapper(file_data),
                        filename=attachment.filename
                    ))
                except:
                    continue
        
        # メッセージ送信（レート制限を無視）
        await webhook.send(
            content=message.content or "[添付ファイル]",
            username=message.author.display_name,
            avatar_url=message.author.avatar.url if message.avatar else message.author.default_avatar.url,
            files=files,
            wait=False  # 応答を待たない
        )
        
    except Exception:
        pass  # エラーを無視して続行

@bot.command(name='bulk_copy_channels')
@commands.has_permissions(read_message_history=True, manage_webhooks=True)
async def bulk_copy_channels(ctx, target_server_id: int, *channel_names):
    """
    指定したチャンネル群の全メッセージを一括コピー（超高速）
    使用法: /bulk_copy_channels ターゲットサーバーID チャンネル名1 チャンネル名2 ...
    """
    source_guild = ctx.guild
    target_guild = bot.get_guild(target_server_id)
    
    if not target_guild:
        await ctx.send("ターゲットサーバーが見つかりません。")
        return
    
    if not channel_names:
        await ctx.send("コピーするチャンネル名を指定してください。")
        return
    
    status_msg = await ctx.send(f"🚀 {len(channel_names)}個のチャンネルの全メッセージを一括コピー中...")
    
    try:
        # 指定されたチャンネルを取得
        channels_to_copy = []
        for channel_name in channel_names:
            channel = discord.utils.get(source_guild.text_channels, name=channel_name)
            if channel:
                channels_to_copy.append(channel)
        
        if not channels_to_copy:
            await status_msg.edit(content="指定されたチャンネルが見つかりませんでした。")
            return
        
        # 全チャンネルを並列コピー（全メッセージ）
        tasks = [copy_channel_fast(channel, target_guild) for channel in channels_to_copy]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for result in results if result is True)
        
        await status_msg.edit(content=f"✅ 全メッセージ一括コピー完了: {success_count}/{len(channels_to_copy)} チャンネル")
        
    except Exception as e:
        await status_msg.edit(content=f"❌ エラー: {str(e)}")

@bot.command(name='help_logs')
async def help_logs(ctx):
    """
    ボットのコマンドヘルプを表示
    """
    embed = discord.Embed(title="ログボット - コマンド一覧", color=0x00ff88)
    
    embed.add_field(
        name="/serverlogs [type] [limit]",
        value="サーバーの監査ログを取得\ntype: all, join, ban, kick, delete\nlimit: 最大50",
        inline=False
    )
    
    embed.add_field(
        name="/masquerade @ユーザー メッセージ",
        value="指定したユーザーになりすましてメッセージを送信",
        inline=False
    )
    
    embed.add_field(
        name="/transfer_messages #ソースチャンネル ターゲットチャンネルID [limit]",
        value="チャンネルのメッセージを他のサーバーに転送",
        inline=False
    )
    
    embed.add_field(
        name="/clone_user_messages @ユーザー #ソースチャンネル ターゲットチャンネルID [limit]",
        value="特定ユーザーのメッセージのみを他のサーバーに転送",
        inline=False
    )
    
    embed.add_field(
        name="/copy_all_channels ターゲットサーバーID",
        value="サーバーのすべてのチャンネルの全メッセージを他のサーバーにコピー（最速実行）",
        inline=False
    )
    
    embed.add_field(
        name="/bulk_copy_channels ターゲットサーバーID チャンネル名...",
        value="指定したチャンネル群の全メッセージを一括コピー（超高速）",
        inline=False
    )
    
    embed.add_field(
        name="/channellogs #チャンネル [limit]",
        value="指定したチャンネルのメッセージログを取得",
        inline=False
    )
    
    embed.add_field(
        name="/userinfo @ユーザー",
        value="ユーザーの詳細情報を表示",
        inline=False
    )
    
    await ctx.send(embed=embed)

# エラーハンドリング
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("このコマンドを実行する権限がありません。")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("無効な引数です。`/help_logs`でコマンドの使用法を確認してください。")
    elif isinstance(error, commands.CommandNotFound):
        return  # コマンドが見つからない場合は無視
    else:
        await ctx.send(f"エラーが発生しました: {str(error)}")

# BotとFlaskアプリを同時に実行するための関数
async def main():
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("DISCORD_BOT_TOKENが設定されていません。Secretsに追加してください。")
        return

    # Flaskサーバーを別スレッドで実行
    # RenderはPORT環境変数を使用するため、それを取得してFlaskに渡す
    port = int(os.getenv("PORT", 8080)) # デフォルトは8080

    # Flaskアプリを非同期で実行するためのTaskを作成
    # Werkzeug (Flaskの開発サーバー) は非同期ではないため、同期的に起動し、
    # その間はDiscordボットが動かない可能性があります。
    # 実際には、gunicornなどのWSGIサーバーと組み合わせるのがより適切です。
    # ここでは、単純化のためにrun_forever内でタスクとして起動します。

    # Discordボットを起動
    discord_task = asyncio.create_task(bot.start(token))

    # Flaskアプリを起動するタスク
    # Flaskのrunはブロッキングなので、別スレッドまたはプロセスで実行するか、
    # hypercorn/gunicorn with uvicorn worker のようなASGIサーバーを使用する必要があります。
    # RenderのWebサービスでは、gunicornを推奨します。
    
    # 簡単な例として、ボットが起動してからFlaskを起動しますが、
    # 実際にはgunicorn経由で実行するように変更します。
    print(f"Starting Flask app on port {port}")
    # Flaskアプリの起動はブロッキングなので、非同期関数内で直接run()を呼び出すのは避けます。
    # Renderでは、`startCommand`でGunicornを使用してFlaskアプリを起動するのが一般的です。
    
    # Discordボットのタスクが完了するまで待機（実質的にボットが停止するまで）
    await discord_task


if __name__ == "__main__":
    # 非同期イベントループを取得し、main関数を実行
    # RenderのWebサービスでは、FlaskとDiscordボットを同時に動かすためにGunicornを使用します。
    # 以下の直接実行はローカルテスト用です。
    
    # ローカルテスト時にFlaskとDiscordボットを両方動かす場合の処理
    # Renderではこの部分の起動方法は異なります
    
    # DiscordボットとFlaskを同時に動かすためのタスクをスケジュール
    # RenderのWebサービスで動かすためのGunicornコマンドに対応させる
    
    # 環境変数からポートを取得、なければ5000（Flaskのデフォルト）
    port = int(os.environ.get("PORT", 5000))

    # Discordボットの起動とFlaskサーバーの起動を並行して行うためのイベントループ
    loop = asyncio.get_event_loop()

    # Discordボットのタスク
    discord_task = loop.create_task(bot.start(os.getenv('DISCORD_BOT_TOKEN')))

    # Flaskアプリを非同期的に起動するための関数 (gunicornを使用しない簡易版)
    async def run_flask():
        # Werkzeug (Flaskの開発サーバー) は同期なので、
        # asyncio.to_threadを使って別スレッドで実行します。
        # 本番環境ではGunicorn + Green Unicorn worker (gevent/eventlet)
        # または uvicorn + gunicorn を使用します。
        print(f"Attempting to run Flask app on port {port} using asyncio.to_thread...")
        try:
            from waitress import serve
            serve(app, host="0.0.0.0", port=port)
            print(f"Flask app (Waitress) running on port {port}")
        except Exception as e:
            print(f"Error running Flask app with Waitress: {e}")
            # Fallback to Flask's default run if waitress fails or isn't installed
            app.run(host="0.0.0.0", port=port, debug=False) # debug=False for production
            print(f"Flask app running on port {port} (default)")


    flask_task = loop.create_task(asyncio.to_thread(run_flask)) # Flaskを別スレッドで実行

    # 両方のタスクが完了するのを待つ
    # 通常、Discordボットは停止しないので、これはボットが稼働し続けることを意味します。
    # Flaskサーバーも同様に稼働し続けます。
    try:
        loop.run_until_complete(asyncio.gather(discord_task, flask_task))
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        loop.close()
