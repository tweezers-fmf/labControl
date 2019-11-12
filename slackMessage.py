"""
    Module for sending notifications to my Slack channel gregorin.slack.com
"""

import slack
import os

USER = 'Ziga-PySlackAPI'
_TOKEN = os.environ.get('SLACK_TOKEN')

client = slack.WebClient(token=_TOKEN)


def sendMessage(message, channel='#sandbox'):
    response = client.chat_postMessage(
        channel=channel,
        text=message,
        username=USER
    )
    return response['ok']


@slack.RTMClient.run_on(event='message')
def say_hello(**payload):
    # print(payload.keys())
    data = payload['data']
    # print(data)
    web_client = payload['web_client']
    # rtm_client = payload['rtm_client']
    if 'text' in data.keys():
        print(data['text'])
        if 'Hello' in data['text']:
            channel_id = data['channel']
            thread_ts = data['ts']
            user = data['user']

            web_client.chat_postMessage(
                channel=channel_id,
                text=f'Hi <@{user}>!',
                thread_ts=thread_ts,
                username=USER
            )
            # print('Done!')


if __name__ == '__main__':

    rtm_client = slack.RTMClient(token=_TOKEN)
    try:
        rtm_client.start()
    except KeyboardInterrupt:
        rtm_client.stop()
