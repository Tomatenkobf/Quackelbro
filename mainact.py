#!/usr/bin/python3.10

from telethon import TelegramClient,events
import RPi.GPIO as GPIO
import os
import yaml
from time import sleep
import asyncio
import signal
#import board
from random import randint

"""
initialisation of GPIOs
"""

global recLED      #led recording (mic+)
global recBUT      #button recording (mic+)
global playLED     #led you have a voicemail

global toPlay      # number of voicemail waiting
global recD        # duration of recording (in half second)
global playOK      # autorisation to play messages (boolean)
global playOKD     # timeout(en 1/2 secondes) de l'autorisation


global heartBeatLed #heartbeat effect on led
global motor

heartBeatLed = False


playOK = False
recD = 0
playOKD = 0
button_counter = 0
time_var = 0

pinS0 = 27
pinS1 = 22
toPlay = -1
playLED = 10
recLED = 25
recBUT = 23
motor = 17


"""
initialisation of GPIO leds and switch 
"""

#GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(recLED, GPIO.OUT)
GPIO.setup(recBUT, GPIO.IN)
GPIO.setup(pinS0, GPIO.OUT)
GPIO.setup(pinS1, GPIO.OUT)
#GPIO.setup(shutBUT, GPIO.IN,pull_up_down=GPIO.PUD_UP)
#GPIO.add_event_detect(shutBUT,GPIO.FALLING)
GPIO.setup(playLED, GPIO.OUT)
GPIO.setup(motor, GPIO.OUT)
GPIO.output(recLED, GPIO.LOW)

#read config file
with open('/home/tomatenkobf/web/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

audio_gain_notification = config['audio_gain_notification']
audio_gain_voice = config['audio_gain_voice']
print("audio gain notification is" + str(audio_gain_notification))
print("audio gain voice is" + str(audio_gain_voice))
# Use your own values from my.telegram.org
api_id = config['api_id']
api_hash = config['api_hash']
client = TelegramClient('anon', api_id, api_hash)


@client.on(events.NewMessage)
async def my_event_handler(event):
    if 'get config' in event.raw_text:
        #read config file
        with open('/home/tomatenkobf/web/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        #print config with new line after each key:value pair
        await event.reply('\n'.join('{}: {}'.format(key, val) for key, val in config.items()))
        #await event.reply('hi!')

        

async def timeC():
    """
    time management : duration of recording and timeout for autorization to play
    """
    global playOK
    global playOKD
    global recD

    while True :
        await asyncio.sleep(0.5)
        recD = recD + 1
        if playOK == True:
            playOKD = playOKD - 1
            if playOKD <= 0:
                playOK = False



async def recTG():
    """
    Send a message 'voice'
    initialisation of gpio led and button
    when button is pushed: recording in a separate process
    that is killed when the button is released
    conversion to .oga by sox
    """
    global recD
    global playOK
    global playOKD
    delay = 0.2 
    while True:    
        await asyncio.sleep(delay)
        if GPIO.input(recBUT) == GPIO.LOW:
            heartBeatLed = False
            GPIO.output(pinS1, GPIO.LOW)
            recD = 0

            # Start recording process asynchronously
            record_cmd = [
                '/usr/bin/arecord',
                '-f',
                'S16_LE',
                '-c1',
                '-r44100',
                '/home/tomatenkobf/quackelbro/rec.wav'
            ]
            record_process = await asyncio.create_subprocess_exec(
                *record_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            while GPIO.input(recBUT) == GPIO.LOW:
                await asyncio.sleep(delay)

            record_process.terminate()  # Terminate the recording process
            await record_process.wait()

            heartBeatLed = False
            playOK = True
            playOKD = 30
            if recD > 1:
                os.system('sudo killall sox')
                os.system('/usr/bin/sox /home/tomatenkobf/quackelbro/rec.wav /home/tomatenkobf/quackelbro/rec.ogg')
                os.rename('/home/tomatenkobf/quackelbro/rec.ogg', '/home/tomatenkobf/quackelbro/rec.oga')
                await client.send_file('Tomatenkobf', '/home/tomatenkobf/quackelbro/rec.oga', voice_note=True)
        else:
            GPIO.output(pinS1, GPIO.HIGH)

async def play_audio(name):
    cmd = ['/usr/bin/cvlc', name, '--play-and-exit', '--gain=' + str(audio_gain_voice)]

    try:
        # Create the subprocess to play the audio
        process = await asyncio.create_subprocess_exec(*cmd)

        # Wait for the process to finish
        await process.wait()

        print("Now Playing:", name)

    except asyncio.CancelledError:
        # If the task is cancelled, terminate the subprocess
        process.terminate()
        await process.wait()

    except Exception as e:
        # Handle other exceptions (e.g., FileNotFoundError, etc.)
        print(f"Error while playing {name}: {e}")


async def playTG():
    """
    when authorized to play (playOK == True)
    play one or several messages waiting (file .ogg) playLED on
    message playing => playing
    last message waiting => toPlay
    """
    global toPlay
    global playOk
    global playOKD

    global heartBeatLed
    global servo

    playing = 0
    while True:
        if toPlay >= 0:
            #print("toPlay = ", toPlay)
            GPIO.output(playLED, GPIO.HIGH)
            heartBeatLed = True
            GPIO.output(pinS0, GPIO.LOW)
            
        else:
            GPIO.output(playLED, GPIO.LOW)
            heartBeatLed = False
            GPIO.output(pinS0, GPIO.HIGH)

            
        if (toPlay >= 0) and (playOK == True):
            while playing <= toPlay:
                name = '/home/tomatenkobf/quackelbro/received_msgs/play' + str(playing) + '.ogg'
                print("playing = ", playing, " name = ", name)
                os.system('sudo killall vlc')

                await play_audio(name)

                playing = playing + 1

                if playing <= toPlay :
                    await asyncio.sleep(1)
            playing = 0
            toPlay = -1  
            #playOk = True
            #playOKD = 30     
        await asyncio.sleep(0.2)


@client.on(events.NewMessage)
async def receiveTG(event):
    global toPlay

    fromName = config['username']
    
    #only plays messages sent by your correpondant, if you want to play messages from everybody comment next line and uncomment the next next line
    if (event.media.document.mime_type  == 'audio/ogg'):
    #if (event.media.document.mime_type == 'audio/ogg'): 
            ad = await client.download_media(event.media)
            #print('ok')
            print(toPlay)
            toPlay =  toPlay + 1
            if toPlay == 0:
                os.system('/usr/bin/cvlc --play-and-exit --gain=' + str(audio_gain_notification) + ' /home/tomatenkobf/quackelbro/toene/notification.wav')
            name = '/home/tomatenkobf/quackelbro/received_msgs/play' + str(toPlay) +  '.ogg'
            #print(name)
            os.rename(ad,name)
            await asyncio.sleep(0.2)
            #os.system('/usr/bin/cvlc --play-and-exit ' +  name)


def wait_for_code():
    while True:
        with open('/home/tomatenkobf/web/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        if config['auth_code'] != '':
            buf = config['auth_code']
            config['auth_code'] = ''
            config['is_auth'] = 'checked'
            with open('/home/tomatenkobf/web/config.yaml', 'w') as f:
                yaml.safe_dump(config, f)
            return buf
        elif config['is_auth'] != '':
            config['is_auth'] = ''
            with open('/home/tomatenkobf/web/config.yaml', 'w') as f:
                yaml.safe_dump(config, f)
        print("Waiting for auth code...")
        sleep(5)


client.start(phone=config['phonenumber'], code_callback=wait_for_code)


os.system('/usr/bin/cvlc --play-and-exit --gain=' + str(audio_gain_notification) + ' /home/tomatenkobf/quackelbro/toene/flute_notification.wav')
loop = asyncio.get_event_loop()
loop.create_task(recTG())
loop.create_task(playTG())
loop.create_task(timeC())
loop.run_forever()
client.run_until_disconnected()