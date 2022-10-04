from flask import Flask, request, render_template, Response, send_from_directory
from jinja2 import Template
import waitress
import logging
import re
import graphyte
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()


class MiniTracker:
    def __init__(self):
        graphite_host = os.getenv('GRAPHITE_HOST', False)
        graphite_prefix = os.getenv('GRAPHITE_PREFIX', False)
        if not graphite_host:
            raise RuntimeError('Missing environment variable GRAPHITE_HOST')
        if not graphite_prefix:
            raise RuntimeError('Missing environment variable GRAPHITE_PREFIX')

        graphyte.init(graphite_host, prefix=graphite_prefix)

        self.logger = self.__init_logger()

    def __init_logger(self):
        if os.getenv('STAGE', False) == 'dev':
            log_level = logging.DEBUG
        else:
            log_level = logging.INFO

        logging.basicConfig(
            format='%(asctime)s %(levelname)-8s %(message)s',
            level=log_level,
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        this_logger = logging.getLogger()
        return this_logger

    def __send_metric(self, metric, value):
        self.logger.debug('Metric: ' + metric + ', ' + str(value))
        graphyte.send(metric, value)

    def __generate_error_page(self, status_code, status_message):
        page = Path('templates/status.html').read_text()
        tpl_page = Template(page)

        return tpl_page.render({'status_code': status_code, 'status_message': status_message})

    def __categorize_file(self, filename):

        file_ext = self.__get_file_extension(filename)
        if file_ext:

            if file_ext in ['pdf', 'docx', 'epub', 'odt']:
                if 'obs-tq' in filename:
                    return 'tq'
                elif 'obs-tn' in filename:
                    return 'tn'
                elif 'obs-sn' in filename:
                    return 'sn'
                elif 'obs-sq' in filename:
                    return 'sq'
                else:
                    return 'stories'
            elif file_ext in ['mp3', '3gp']:
                return 'audio'
            elif file_ext in ['mp4']:
                return 'video'
            elif file_ext in ['zip']:
                if 'mp3' in filename:
                    return 'audio'
                elif 'mp4' in filename or '3gp' in filename:
                    return 'video'
                elif 'obs-tq' in filename:
                    return 'tq'
                elif 'obs-tn' in filename:
                    return 'tn'
                elif 'obs-sn' in filename:
                    return 'sn'
                elif 'obs-sq' in filename:
                    return 'sq'
                else:
                    return 'stories'

        return False

    def home(self):
        return render_template('home.html')

    def __get_file_extension(self, filename):
        if filename:
            file_ext = os.path.splitext(filename)
            if len(file_ext) == 2:
                return file_ext[1].replace('.', '')

        return False

    def download_logger(self):
        referrer = request.headers.get('Referer')
        useragent = request.headers.get('User-Agent')

        self.logger.debug('User agent : ' + str(useragent))
        self.logger.debug('Referer : ' + str(referrer))

        # Only valid user agents
        if "Mozilla" in useragent:
            # We don't want bots. We might want to update this to a filter list...
            if not re.search("[bB]ot", useragent):
                # Check for valid referer. Currently, that is only the OBS website
                allowed_referer = "https://www.openbiblestories.org"
                if referrer and allowed_referer in referrer:

                    lc = request.args.get('lang')
                    dl_file = request.args.get('file')

                    if lc and dl_file:

                        # Ignore non-files for now
                        lst_ignore_files = ['View%20on%20Door43.org', 'YouTube']
                        if dl_file not in lst_ignore_files:

                            file_ext = self.__get_file_extension(dl_file)
                            category = self.__categorize_file(dl_file)

                            if file_ext and category:

                                self.logger.debug('File : ' + str(dl_file))
                                self.logger.debug('Category : ' + str(category))
                                self.logger.debug('Filetype : ' + str(file_ext))
                                self.logger.debug('LC : ' + str(lc))

                                metric = lc + '.' + category + '.' + file_ext

                                self.__send_metric(metric, 1)

                                response = Response('', status=204)
                                return response

                            else:
                                self.logger.warning("File %s could not be correctly parsed" % dl_file)

        # If a check fails, we simply send a Status 400 - Bad Request
        status_code = 400
        text = self.__generate_error_page(status_code, 'Bad request')

        response = Response(text, status=status_code)
        return response


# Initialize
app = Flask(__name__, static_folder='static')
mt = MiniTracker()


# Routing
@app.route('/log/downloads')
def download_logger():
    return mt.download_logger()


@app.route('/')
def track_home():
    return mt.home()


@app.route("/favicon.ico")  # Load the favicon
def fav():
    return send_from_directory(app.static_folder, 'favicon.ico')  # for sure return the file


# Main
if __name__ == '__main__':
    host = '0.0.0.0'
    port = 3033

    if os.getenv('STAGE', False) == 'dev':
        app.run(host=host, port=port, debug=True)
    else:
        waitress.serve(app, host=host, port=port)
