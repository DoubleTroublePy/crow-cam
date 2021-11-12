from threading import Thread, Lock
from dotenv import load_dotenv
from discord.ext import tasks, commands
import numpy as np
import datetime
import imutils
import discord
import struct
import socket
import pickle
import shutil
import time
import cv2
import os


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
channel_ID = 827947323816149013

bot = commands.Bot(command_prefix="!")

lock = Lock()
arg = {
    'video_send': True,
    'frame': [],
    'frame_status': False,
    'ready': 0,
    'root': 'E:/GitHub/progetti/crow-cam/',
    'video_root': '',
    'ip': ''
}
arg['video_root']= arg['root'] + 'video/'


class MultiThread(Thread):
    __frame_old = []

    def __init__(self, thread_id):
        Thread.__init__(self)
        self.thread_id = thread_id

    def run(self):
        if self.thread_id == 1:
            self.thread_cam()
        elif self.thread_id == 2:
            while True:
                if not lock.locked():
                    bot.run(TOKEN)
                    break
        elif self.thread_id == 3:
            while True:
                if not lock.locked():
                    self.cam_stream()
                    break

    def thread_cam(self):
        def brightness(img):
            if len(img.shape) == 3:
                # Colored RGB or BGR (*Do Not* use HSV images with this function)
                # create brightness with euclidean norm
                return np.average(img) / np.sqrt(3)
            else:
                # Grayscale
                return np.average(img)

        def video_save(video_name, img_array):
            print('... video saving ...', video_name)
            if os.path.isfile(video_name):
                os.remove(video_name)
            height, width, layers = img_array[0].shape
            size = (width, height)

            out = cv2.VideoWriter(video_name, 0x7634706d, 20.0, (640, 480))
            for i in range(len(img_array)):
                out.write(img_array[i])
            out.release()

        def rectangle(thresh, img):
            cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
                                    cv2.CHAIN_APPROX_SIMPLE)
            cnts = imutils.grab_contours(cnts)
            # loop over the contours
            for c in cnts:
                # if the contour is too small, ignore it
                if cv2.contourArea(c) < 500:
                    continue
                (x, y, w, h) = cv2.boundingRect(c)
                cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
            return img

        clip = []
        clip_1 = []
        cam_show = True
        cam_index = 0
        # input

        lock.acquire()

        tmp_root = input('Enter the video path, leave blank for default >>> ')
        if tmp_root != '':
            arg['root'] = tmp_root

        tmp_cam_index = input('Enter the camera index, leave blank for default >>> ')
        if tmp_cam_index != '':
            cam_index = int(tmp_cam_index)

        tmp_cam_show = input('Show the camera? (y/n) >>> ')
        if tmp_cam_show == 'y':
            cam_show = True
        else:
            cam_show = False

        cap = cv2.VideoCapture(cam_index)
        if not (cap.isOpened()):
            print("Could not open video device")

        lock.release()

        # start
        timer = 0
        timer_on = False

        previous = None

        ret, frame = cap.read()
        while True:
            arg['frame_status'] = False
            ret, arg['frame'] = cap.read()
            height, width, channels = frame.shape

            grey = cv2.cvtColor(arg['frame'], cv2.COLOR_BGR2GRAY)
            grey = cv2.GaussianBlur(grey, (21, 21), 0)

            if previous is not None:
                diff = cv2.absdiff(previous, grey)

                diff = cv2.erode(diff, None, iterations=2)
                diff = cv2.dilate(diff, None, iterations=2)

                _, diff = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
                if cam_show:
                    cv2.imshow('diff', diff)
                if brightness(diff) > 5:
                    timer_on = True
                    timer = time.time()

                if timer_on:
                    # cv2.putText(frame, "Motion detected", (10, 450),
                    #             cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
                    clip_1.append(arg['frame'])
                    img = rectangle(diff, arg['frame'].copy())
                    clip.append(img)

                    if time.time() - timer > 1:
                        timer_on = False
                        timer = time.time()
                        video_save(str(arg['video_root']) + "motion_" '%s_%s_%s_%s_%s' % (date.year, date.month, date.day,
                                                                    date.hour, date.minute) + ".mp4",np.array(clip))
                        clip = []
                        clip_1 = []

            previous = grey.copy()

            # overlay the date and time on the frame
            date = datetime.datetime.now()
            cv2.putText(arg['frame'], 'date:%s-%s-%s time:%s:%s:%s' %
                        (date.year, date.month, date.day, date.hour, date.minute, date.second),
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.threshold(grey, 127, 255, cv2.THRESH_BINARY, grey)
            arg['frame_status'] = True
            grey = cv2.dilate(grey, None, iterations=2)

            if cam_show:
                cv2.imshow('cam', arg['frame'])
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

    def cam_stream(self):
        global arg
        # Socket Create
        lock.acquire()

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        host_name = socket.gethostname()
        host_ip = socket.gethostbyname(host_name)
        print('HOST IP:', host_ip)
        port = 9999
        socket_address = (host_ip, port)

        # Socket Bind
        server_socket.bind(socket_address)

        # Socket Listen
        server_socket.listen(5)
        print("LISTENING AT:", socket_address)
        arg['ip'] = socket_address
        lock.release()
        # Socket Accept
        while True:
            client_socket, addr = server_socket.accept()
            print('GOT CONNECTION FROM:', addr)
            if client_socket:
                while True:
                    if arg['frame_status']:
                        a = pickle.dumps(arg['frame'].copy())
                        self.__frame_old = arg['frame'].copy()
                        message = struct.pack("Q", len(a)) + a
                    elif self.__frame_old != []:
                        a = pickle.dumps(self.__frame_old)
                        message = struct.pack("Q", len(a)) + a
                    try:
                        client_socket.sendall(message)
                    except Exception as e:
                        if e.args[0] != "local variable 'message' referenced before assignment":
                            print(e)
                        if e.args[0] == 10054:  # if client is disconnected then break
                            break

                    if cv2.waitKey(1) == '13':
                        client_socket.close()


@bot.event
async def on_ready():
    await bot.wait_until_ready()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="a crow"))
    print("Logged in as:")
    print(bot.user.name)
    print("------")
    channel = bot.get_channel(channel_ID)
    print("Channel is:")
    print(channel)  # Prints None
    loop.start()


@bot.event
async def on_message(message):
    global arg
    if message.author == bot.user:
        return

    # comands
    if message.content.startswith('-stop'):
        await message.channel.send('... stopped ...')
        video_send = False

    if message.content.startswith('-start'):
        await message.channel.send('... started ...')
        video_send = True

    if message.content.startswith('-status'):
        await message.channel.send('... ' + str(arg['video_send']) + ' ...')

    if message.content.startswith('-queue') and ' ' not in message.content:
        queue = ''
        for file in os.listdir(arg['video_root']):
            if file.endswith('.mp4') and '_done' not in file:
                queue += file + '\n'
        if queue != '':
            await message.channel.send(queue)
        else:
            await message.channel.send('... queue empty ...')

    if message.content.startswith('-queue clear'):
        for file in os.listdir(arg['video_root']):
            if file.endswith('.mp4') and '_done' not in file:
                time.sleep(.1)
                await message.channel.send(file=discord.File(arg['video_root'] + '/' + file))
                shutil.move(arg['video_root'] + '/' + file, arg['video_root'] + '/' + file.replace('.', '_done.'))
                time.sleep(.1)

    if message.content.startswith('-queue send'):
        for file in os.listdir(arg['video_root']):
            if file.endswith('.mp4') and '_done' not in file:
                time.sleep(.1)
                await message.channel.send(file=discord.File(arg['video_root'] + '/' + file))
                shutil.move(arg['video_root'] + '/' + file, arg['video_root'] + '/' + file.replace('.', '_done.'))
                time.sleep(.1)
    if message.content.startswith('-ip'):
        time.sleep(.1)
        await message.channel.send(arg['ip'])
        time.sleep(.1)
    if message.content.startswith('-help'):
        await message.channel.send("""
                                   -start --> to start the bot\n
                                   -stop --> to stop the bot\n
                                   -status --> to check the status of the bot\n
                                   -queue --> to show the queue\n
                                   -ip --> to show the ip \n
                                   -help --> to show this message
                                   """)


@tasks.loop(seconds=0)
async def loop():
    await bot.wait_until_ready()
    channel = bot.get_channel(channel_ID)
    for file in os.listdir(arg['video_root']):
        if '_done' not in file:
            if arg['video_send']:
                try:
                    time.sleep(.1)
                    await channel.send(file=discord.File(arg['video_root'] + '/' + file))
                    shutil.move(arg['video_root'] + '/' + file, arg['video_root'] + '/' + file.replace('.', '_done.'))
                    time.sleep(.1)
                except Exception as e:
                    print(e)

if __name__ == '__main__':
    t1 = MultiThread(1)
    t1.start()
    t3 = MultiThread(3)
    t3.start()
    t2 = MultiThread(2)
    t2.start()

    t2.join()
