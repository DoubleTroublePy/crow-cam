from threading import Thread, Lock
import numpy as np
lock = Lock()


class Thread(Thread):
    def __init__(self, thread_ID):
        Thread.__init__(self)
        self.thread = thread_ID
        self.start()

    def run(self):
        if self.thread_ID == 1:
            self.thread_cam()
        elif self.thread_ID == 2:
            pass
        elif self.thread_ID == 3:
            pass

    def thread_cam(self):
        def brightness(img):
            if len(img.shape) == 3:
                # Colored RGB or BGR (*Do Not* use HSV images with this function)
                # create brightness with euclidean norm
                return np.average(img) / np.sqrt(3)
            else:
                # Grayscale
                return np.average(img)

        root = './video'
        cam_index = 0
        cam_show = True

        lock.acquire()

        tmp_root = input('Enter the path to the video, leave blank for default >> ')
        tmp_cam_index = input('Enter the cam index, leave blank for default >> ')
        tmp_cam_show = input('show the camera? y/n >> ')

        if tmp_root:
            root = tmp_root

        if tmp_cam_index:
            cam_index = int(tmp_cam_index)

        if tmp_cam_show == 'y':
            cam_show = True
        elif tmp_cam_show == 'n':
            cam_show = False

        lock.release()


if __name__ == '__main__':
    Thread(1)
    Thread(2)
    Thread(3)
