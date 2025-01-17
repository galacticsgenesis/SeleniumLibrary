# Copyright 2008-2011 Nokia Networks
# Copyright 2011-2016 Ryan Tomac, Ed Manlove and contributors
# Copyright 2016-     Robot Framework Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

from robot.utils import get_link_path
import threading
import time
from SeleniumLibrary.base import LibraryComponent, keyword
from SeleniumLibrary.utils import is_noney
import cv2


class ScreenshotKeywords(LibraryComponent):

    @keyword
    def set_screenshot_directory(self, path):
        """Sets the directory for captured screenshots.

        ``path`` argument specifies the absolute path to a directory where
        the screenshots should be written to. If the directory does not
        exist, it will be created. The directory can also be set when
        `importing` the library. If it is not configured anywhere,
        screenshots are saved to the same directory where Robot Framework's
        log file is written.

        The previous value is returned and can be used to restore
        the original value later if needed.

        Returning the previous value is new in SeleniumLibrary 3.0.
        The persist argument was removed in SeleniumLibrary 3.2.
        """
        if is_noney(path):
            path = None
        else:
            path = os.path.abspath(path)
            self._create_directory(path)
        previous = self.ctx.screenshot_root_directory
        self.ctx.screenshot_root_directory = path
        return previous

    @keyword
    def capture_page_screenshot(self, filename='selenium-screenshot-{index}.png'):
        """Takes screenshot of the current page and embeds it into log file.

        ``filename`` argument specifies the name of the file to write the
        screenshot into. The directory where screenshots are saved can be
        set when `importing` the library or by using the `Set Screenshot
        Directory` keyword. If the directory is not configured, screenshots
        are saved to the same directory where Robot Framework's log file is
        written.

        Starting from SeleniumLibrary 1.8, if ``filename`` contains marker
        ``{index}``, it will be automatically replaced with unique running
        index preventing files to be overwritten. Indices start from 1,
        and how they are represented can be customized using Python's
        [https://docs.python.org/3/library/string.html#format-string-syntax|
        format string syntax].

        An absolute path to the created screenshot file is returned.

        Examples:
        | `Capture Page Screenshot` |                                        |
        | `File Should Exist`       | ${OUTPUTDIR}/selenium-screenshot-1.png |
        | ${path} =                 | `Capture Page Screenshot`              |
        | `File Should Exist`       | ${OUTPUTDIR}/selenium-screenshot-2.png |
        | `File Should Exist`       | ${path}                                |
        | `Capture Page Screenshot` | custom_name.png                        |
        | `File Should Exist`       | ${OUTPUTDIR}/custom_name.png           |
        | `Capture Page Screenshot` | custom_with_index_{index}.png          |
        | `File Should Exist`       | ${OUTPUTDIR}/custom_with_index_1.png   |
        | `Capture Page Screenshot` | formatted_index_{index:03}.png         |
        | `File Should Exist`       | ${OUTPUTDIR}/formatted_index_001.png   |
        """
        if not self.drivers.current:
            self.info('Cannot capture screenshot because no browser is open.')
            return
        path = self._get_screenshot_path(filename)
        self._create_directory(path)
        if not self.driver.save_screenshot(path):
            raise RuntimeError("Failed to save screenshot '{}'.".format(path))
        self._embed_to_log(path, 800)
        return path

    @keyword("Screen Record Start")
    def capture_screenshots(self, filename='screenshots-{index}.png'):
        global screen_video_queue
        try:
            isinstance(screen_video_queue, list)
        except NameError:
            screen_video_queue = []
        screenshots = []
        screen_video_queue.append([0, True, screenshots, False])  # 队列中放一个列表，列表第一位放运行时间，第二位放是否录制开关，第三位放录制文件列表
        index = len(screen_video_queue) - 1
        self.info('start screen record with index : {}'.format(index))
        threading.Thread(target=self._loop_capture_screenshots, args=(index, filename)).start()
        return index

    def _loop_capture_screenshots(self, index, filename):
        global screen_video_queue
        start_time = time.time()
        while screen_video_queue[index][1]:
            try:
                path = self._get_video_image_path(filename)
                self._create_directory(path)
                if self.driver.save_screenshot(path):
                    screen_video_queue[index][2].append(path)
                screen_video_queue[index][0] = time.time() - start_time
            except:
                self.info('Cannot capture screenshots')
                time.sleep(1)
        screen_video_queue[index][3] = True

    @keyword("Screen Record Stop")
    def stop_recording_and_save_to_mp4(self, index, video_name='video-{index}.mp4'):
        global screen_video_queue
        try:
            isinstance(screen_video_queue, list)
        except NameError:
            raise RuntimeError("screen video queue is not init")

        if index is None or int(index) >= len(screen_video_queue):
            raise RuntimeError("index is null or invalid, please make sure index is correct")
        index = int(index)
        self.info('stop screen record and save with index : {}'.format(index))
        screen_video_queue[index][1] = False
        wait_finishing_record_count = 0
        while not screen_video_queue[index][3]:
            time.sleep(1)
            wait_finishing_record_count += 1
            if wait_finishing_record_count == 5:
                self.info('screenshots for index {} cannot stop'.format(index))
                return
        self.info('wait {} seconds util finishing record'.format(wait_finishing_record_count))
        self.info('video record time {}, length of picture list {}'.format(screen_video_queue[index][0],
                                                                           len(screen_video_queue[index][2])))
        if screen_video_queue[index][0] != 0 and len(screen_video_queue[index][2]) > 0:
            fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
            fps = int(len(screen_video_queue[index][2]) / screen_video_queue[index][0])
            if fps < 1 or len(screen_video_queue[index][2]) < 5:
                fps = 1
            img = cv2.imread(screen_video_queue[index][2][0])  # 获取第一张图片，动态算出尺寸 size
            height, width, channels = img.shape
            size = (width, height)
            path = self._get_video_path(video_name)
            videoWriter = cv2.VideoWriter(path, fourcc, fps, size)
            for i in range(1, len(screen_video_queue[index][2])):
                frame = cv2.imread(screen_video_queue[index][2][i])
                videoWriter.write(frame)
            videoWriter.release()
            self.info('write file done for index : {}'.format(index))

    @keyword
    def capture_element_screenshot(self, locator, filename='selenium-element-screenshot-{index}.png'):
        """Captures screenshot from the element identified by ``locator`` and embeds it into log file.

        See `Capture Page Screenshot` for details about ``filename`` argument.
        See the `Locating elements` section for details about the locator
        syntax.

        An absolute path to the created element screenshot is returned.

        Support for capturing the screenshot from a element has limited support
        among browser vendors. Please check the browser vendor driver documentation
        does the browser support capturing a screenshot from a element.

        New in SeleniumLibrary 3.3

        Examples:
        | `Capture Element Screenshot` | id:image_id |                                |
        | `Capture Element Screenshot` | id:image_id | ${OUTPUTDIR}/id_image_id-1.png |
        """
        if not self.drivers.current:
            self.info('Cannot capture screenshot from element because no browser is open.')
            return
        path = self._get_screenshot_path(filename)
        self._create_directory(path)
        element = self.find_element(locator, required=True)
        if not element.screenshot(path):
            raise RuntimeError("Failed to save element screenshot '{}'.".format(path))
        self._embed_to_log(path, 400)
        return path

    def _get_screenshot_path(self, filename):
        directory = self.ctx.screenshot_root_directory or self.log_dir
        filename = filename.replace('/', os.sep)
        index = 0
        while True:
            index += 1
            formatted = filename.format(index=index)
            path = os.path.join(directory, formatted)
            # filename didn't contain {index} or unique path was found
            if formatted == filename or not os.path.exists(path):
                return path

    def _get_video_image_path(self, filename):
        directory = self.ctx.screenshot_root_directory or self.log_dir
        filename = filename.replace('/', os.sep)
        global g_screenshots_index
        try:
            isinstance(g_screenshots_index, int)
        except NameError:
            g_screenshots_index = 0
        while True:
            g_screenshots_index += 1
            formatted = filename.format(index=g_screenshots_index)
            path = os.path.join(directory, formatted)
            # filename didn't contain {index} or unique path was found
            if formatted == filename or not os.path.exists(path):
                return path

    def _get_video_path(self, filename):
        directory = self.ctx.screenshot_root_directory or self.log_dir
        filename = filename.replace('/', os.sep)
        global g_video_index
        try:
            isinstance(g_video_index, int)
        except NameError:
            g_video_index = 0
        while True:
            g_video_index += 1
            formatted = filename.format(index=g_video_index)
            path = os.path.join(directory, formatted)
            if formatted == filename or not os.path.exists(path):
                return path

    def _create_directory(self, path):
        target_dir = os.path.dirname(path)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

    def _embed_to_log(self, path, width):
        # Image is shown on its own row and thus previous row is closed on
        # purpose. Depending on Robot's log structure is a bit risky.
        self.info('</td></tr><tr><td colspan="3">'
                  '<a href="{src}"><img src="{src}" width="{width}px"></a>'
                  .format(src=get_link_path(path, self.log_dir), width=width), html=True)
