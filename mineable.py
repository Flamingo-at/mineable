import asyncio
import aiohttp

from re import findall
from loguru import logger
from aiohttp import ClientSession
from random import choice, randint
from aiohttp_proxy import ProxyConnector


def random_tor_proxy():
    proxy_auth = str(randint(1, 0x7fffffff)) + ':' + \
        str(randint(1, 0x7fffffff))
    proxies = f'socks5://{proxy_auth}@localhost:' + str(choice(tor_ports))
    return(proxies)


def get_connector():
    connector = ProxyConnector.from_url(random_tor_proxy())
    return(connector)


async def create_email(client: ClientSession):
    try:
        response = await client.get("https://www.1secmail.com/api/v1/?action=genRandomMailbox&count=1")
        email = (await response.json())[0]
        return email
    except:
        logger.error("Failed to create email")
        await asyncio.sleep(1)
        return await create_email(client)


async def check_email(client: ClientSession, login: str, domain: str, count: int):
    try:
        response = await client.get('https://www.1secmail.com/api/v1/?action=getMessages&'
                                    f'login={login}&domain={domain}')
        email_id = (await response.json())[0]['id']
        return email_id
    except:
        while count < 30:
            count += 1
            await asyncio.sleep(1)
            return await check_email(client, login, domain, count)
        logger.error('Emails not found')
        raise Exception()


async def get_link(client: ClientSession, login: str, domain: str, email_id):
    try:
        response = await client.get('https://www.1secmail.com/api/v1/?action=readMessage&'
                                    f'login={login}&domain={domain}&id={email_id}')
        data = (await response.json())['htmlBody']
        link = findall(r'<a href="(.+)">', data)[0]
        return link
    except:
        logger.error('Failed to get link')
        raise Exception()


async def register(client: ClientSession, email: str):
    response = await client.post('https://beta.mineable.io/api/register',
                                 json={

                                     "email": email,
                                     "password": email,
                                     "passwordConfirmation": email,
                                     "referralCode": ref

                                 })
    return((await response.json())['token'])


async def worker():
    while True:
        try:
            async with aiohttp.ClientSession(connector=get_connector()) as client:

                logger.info('Create email')
                email = await create_email(client)

                logger.info('Registration')
                token = await register(client, email)

                logger.info('Check email')
                email_id = await check_email(client, email.split('@')[0], email.split('@')[1], 0)

                logger.info('Get link')
                link = await get_link(client, email.split('@')[0], email.split('@')[1], email_id)

                logger.info('Email confirmation')
                response = await client.get(link)
                if 'Your email was successfully verified' not in str(await response.json()):
                    logger.error(await response.json())
                    raise Exception()

                response = await client.put('https://beta.mineable.io/api/user/backup-complete',
                                            headers={'authorization': f'Bearer {token}'})
                if 'Ok' not in str(await response.json()):
                    logger.error(await response.json())
                    raise Exception()

                response = await client.put('https://beta.mineable.io/api/user/onboarding-complete',
                                            headers={'authorization': f'Bearer {token}'})
                if 'Ok' not in str(await response.json()):
                    logger.error(await response.json())
                    raise Exception()

        except Exception:
            logger.exception("Error\n")
        else:
            with open('registered.txt', 'a', encoding='utf-8') as file:
                file.write(f'{email}:{email}\n')
            logger.success('Successfully\n')

        await asyncio.sleep(delay)


async def main():
    tasks = [asyncio.create_task(worker()) for _ in range(threads)]
    await asyncio.gather(*tasks)


if __name__ == '__main__':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    tor_ports = [9150]

    print("Bot Mineable @flamingoat\n")

    ref = input('Referral code: ')
    delay = int(input('Delay(sec): '))
    threads = int(input('Threads: '))

    asyncio.run(main())