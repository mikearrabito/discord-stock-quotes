import finnhub
import discord
from discord.ext import commands
from datetime import date, timedelta, datetime

api_key = None
discord_token = None

with open("api_key.txt") as file:
    api_key = file.read()

with open("discord_token.txt") as file:
    discord_token = file.read()

if api_key is None:
    raise Exception("API key missing")
if discord_token is None:
    raise Exception("Discord bot token missing")

bot = commands.Bot(command_prefix=".")
finnhub_client = finnhub.Client(api_key)

MONTH_TO_QUARTER = {
    '03': "1",
    '06': "2",
    '09': "3",
    '12': "4"
}

MONTHS = {
    "01": 'Jan',
    "02": "Feb",
    "03": "Mar",
    "04": "Apr",
    "05": "May",
    "06": "Jun",
    "07": "Jul",
    "08": "Aug",
    "09": "Sep",
    "10": "Oct",
    "11": "Nov",
    "12": "Dec"
}


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        # Ignore these errors, this error will trigger when a chat user interacts with another bot with the same prefix
        return
    raise error


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)


@bot.command()
async def price(ctx, arg=""):
    """Returns the current price, and change for the day for a stock symbol"""
    if len(arg) == 0:
        await ctx.send("Invalid symbol")
        return

    arg = arg.upper()
    data = finnhub_client.quote(arg)

    if data['c'] == 0:
        await ctx.send("No data found")
        return

    color = 0x000000

    if data['d'] > 0:
        color = 0x00FF00
    elif data['d'] < 0:
        color = 0xFF0000

    response = discord.Embed(title=arg, color=color)

    response.add_field(name="Current price",
                       value=f"{data['c']}", inline=False)
    response.add_field(name="High", value=f"{data['h']}", inline=True)
    response.add_field(name="Low", value=f"{data['l']}", inline=True)

    response.add_field(name=chr(173), value=chr(173))

    trunc_percent = "{:.2f}".format(data['dp'])
    response.add_field(name="Change", value=f"{data['d']}", inline=True)
    response.add_field(name="Percent change",
                       value=f"{trunc_percent}%", inline=True)

    await ctx.send(embed=response)


@bot.command()
async def cprice(ctx, arg=""):
    """Returns last price for a cryptocurrency"""
    # TODO: finish
    if len(arg) == 0:
        await ctx.send("Invalid symbol")
        return


@bot.command()
async def earnings(ctx, arg=""):
    """Returns actual and estimated EPS for past 4 quarters for a stock"""
    if len(arg) == 0:
        await ctx.send("Invalid symbol")
        return

    earnings_vals = finnhub_client.company_earnings(arg)
    """
    Example response:
    [{
    "actual": 2.56,
    "estimate": 2.38,
    "period": "2019-03-31",
    "symbol": "AAPL"
    },
    ... 
    ]
    """

    if len(earnings_vals) == 0:
        await ctx.send("No data found")
        return

    response = discord.Embed(title=f"Earnings Results for {arg.upper()}")

    for quarter_results in earnings_vals:
        year, month, day = quarter_results['period'].split("-")
        quarter_num = MONTH_TO_QUARTER[month]  # Q1-Q4
        time_period = f"***Q{quarter_num} {year}***"
        results = f"\n\tEstimated EPS: {quarter_results['estimate']}"
        results += f"\n\tActual EPS: {quarter_results['actual']}"
        trunc_percent = "{:.2f}".format(quarter_results['surprisePercent'])
        results += f"\n\tSurprise: {quarter_results['surprise']}\n\tSurprise Percent: {trunc_percent}%"
        response.add_field(name=time_period, value=results)

    await ctx.send(embed=response)
    return


@bot.command()
async def news(ctx, arg=""):
    """
    Returns news for a company from 1 year ago to today
    Shows a maximum of 5 events
    """
    if len(arg) == 0:
        await ctx.send("Invalid symbol")
        return

    from_date = date.today() - timedelta(days=365)
    from_date = from_date.strftime("%Y-%m-%d")
    to_date = date.today().strftime("%Y-%m-%d")

    stock_news = finnhub_client.company_news(arg, from_date, to_date)[:5]
    if len(stock_news) == 0:
        await ctx.send("No data found")
        return

    today_str = date.today().strftime("%m-%d-%Y")
    yesterday_str = date.today() - timedelta(days=1)
    yesterday_str = yesterday_str.strftime("%m-%d-%Y")

    response = discord.Embed(
        title=f"**News for {arg.upper()}**", color=discord.Color.blue())

    for event in stock_news:
        date_of_event = datetime.fromtimestamp(
            event["datetime"]).strftime("%m-%d-%Y")

        if date_of_event == today_str:
            date_of_event = "Today"
        elif date_of_event == yesterday_str:
            date_of_event = "Yesterday"

        response.add_field(
            name=event['source'], value=f"\n***{date_of_event}*** - {event['headline']} Link-{event['url']}")

    await ctx.send(embed=response)


@bot.command()
async def trends(ctx, arg=""):
    """
    Returns analyst recommendations for stock(buy, sell, or hold) on monthly basis
    Will display recommendations for current month, then every previous 6 months for 3 years
    """
    if len(arg) == 0:
        await ctx.send("Invalid symbol")
        return

    arg = arg.upper()

    trends = finnhub_client.recommendation_trends(
        arg)[:36:6]  # 6 results, going back 6 months for each result

    if len(trends) == 0:
        await ctx.send("No data found")
        return

    response = discord.Embed(title=f"Recommendation Trends for {arg}")

    for trend in trends:
        year, month, day = trend['period'].split("-")
        time_period = f"***{MONTHS[month]} {year}***"
        recommendations = f"\n\tStrong buy: {trend['strongBuy']}"
        recommendations += f"\n\tBuy: {trend['buy']}"
        recommendations += f"\n\tHold: {trend['hold']}"
        recommendations += f"\n\tSell: {trend['sell']}"
        recommendations += f"\n\tStrong sell: {trend['strongSell']}"
        response.add_field(name=f"\n{time_period}", value=recommendations)

    await ctx.send(embed=response)

bot.run(discord_token)
