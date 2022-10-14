import flask_cors
from flask import Flask, request, render_template, Response, send_from_directory
from jinja2 import Template
import waitress
import logging
import re
import graphyte
import os
from dotenv import load_dotenv
from pathlib import Path
import json
from flask_cors import CORS

load_dotenv()


class MiniTracker:
    def __init__(self):
        graphite_host = os.getenv('GRAPHITE_HOST', False)
        graphite_prefix = os.getenv('GRAPHITE_PREFIX', False)
        if not graphite_host:
            raise RuntimeError('Missing environment variable GRAPHITE_HOST')
        if not graphite_prefix:
            raise RuntimeError('Missing environment variable GRAPHITE_PREFIX')

        # Init graphite
        graphyte.init(graphite_host, prefix=graphite_prefix)

        # Init logger
        self.logger = self.__init_logger()

        # Loading configuration file
        with open('conf/trackers.conf') as f_trackers:
            self.tracker_config = json.load(f_trackers)

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

    def get_allowed_origins(self):
        # Get allowed CORS origins.
        # If we have no allowed origins defined, we allow everything.
        if 'allowed_origins' in self.tracker_config:
            return self.tracker_config['allowed_origins']

        return '*'

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

    def __load_tracker_config(self, mt_id):
        for config in self.tracker_config['trackers']:
            if config['mt_id'] == mt_id:
                return config

        return None

    def __bot_detected(self, useragent):
        # TODO. Make a better bot detection mechanism, probably based on a bot list
        if re.search("[bB]ot", useragent):
            return True

        return False

    def __convert_parameter_to_metric(self, url_param, parsers):
        for parser in parsers:
            if re.fullmatch(parser['search'], url_param):
                metric = re.sub(parser['search'], parser['metric'], url_param)
                self.logger.debug("URL param '{}' converted to metric '{}'".format(url_param, metric))
                return metric

        return None

    def __sanitize_url_param(self, url_param):
        # Sanitize for TSDB purposes
        new_param = url_param.replace('.', '_')
        return new_param

    def track(self):
        self.logger.debug(request.full_path)
        base_warning = "400 - Bad request"
        mandatory_param_missing = False

        mt_id = request.args.get('mt_id')
        if mt_id:
            config = self.__load_tracker_config(mt_id)
            if config:
                graphite_prefix = config['metric_prefix']

                referrer = request.headers.get('Referer')
                useragent = request.headers.get('User-Agent')

                # Either bots are allowed, or no bot is detected
                if config['allow_bots'] or not self.__bot_detected(useragent):

                    if referrer and config['referer'] in referrer:

                        # At least one url parameter is required
                        if config['url_parameters'] and len(config['url_parameters']) > 0:
                            self.logger.debug(config)

                            lst_metrics = list()

                            for url_param in config['url_parameters']:

                                value = request.args.get(url_param)
                                if value:
                                    param_config = config['url_parameters'][url_param]

                                    if 'converters' in param_config:
                                        conversions = param_config['converters']
                                        metric = self.__convert_parameter_to_metric(value, conversions)
                                    else:
                                        metric = self.__sanitize_url_param(value)

                                    # Insert metric at correct position
                                    pos = 0 # Default if not given
                                    if 'metric_position' in param_config:
                                        pos = param_config['metric_position']
                                    lst_metrics.insert(pos, metric)

                                else:
                                    if 'mandatory' in config['url_parameters'][url_param]:
                                        if config['url_parameters'][url_param]['mandatory'] is True:
                                            mandatory_param_missing = True
                                            self.logger.warning('Mandatory URL param \'{}\' not found in URI string'.format(url_param))

                            # Send off the metric
                            if not mandatory_param_missing:
                                metric = '.'.join(lst_metrics)

                                # Send metric and response
                                self.__send_metric(graphite_prefix + '.' + metric, 1)

                                response = Response('', status=204)
                                return response

                        else:
                            self.logger.warning("{}: No url_parameters defined".format(base_warning))

                    else:
                        self.logger.warning("{}: Invalid referer '{}'".format(base_warning, referrer))

                else:
                    self.logger.warning("{}: Bot detected '{}'".format(base_warning, useragent))

            else:
                self.logger.warning("{}: mt_id '{}' cannot be found in configuration".format(base_warning, mt_id))

        else:
            # No mt_id found.
            self.logger.warning("{}: No mt_id found in URL".format(base_warning))

        # Catch all
        status_code = 400
        text = self.__generate_error_page(status_code, 'Bad request')

        response = Response(text, status=status_code)
        return response

    def download_logger(self):
        my_prefix = 'obs.website.downloads'

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

                                metric = my_prefix + '.' + lc + '.' + category + '.' + file_ext

                                self.__send_metric(metric, 1)

                                response = Response('', status=204)
                                return response

                            else:
                                self.logger.warning("File %s could not be correctly parsed" % dl_file)

        # If a check fails, we simply send a Status 400 - Bad Request
        self.logger.warning("400 - Bad request")

        status_code = 400
        text = self.__generate_error_page(status_code, 'Bad request')

        response = Response(text, status=status_code)
        return response


# Initialize
app = Flask(__name__, static_folder='static')
cors = CORS(app)

mt = MiniTracker()


# Routing
@app.route('/log/downloads')
def download_logger():
    return mt.download_logger()


@app.route('/')
def track_home():
    return mt.home()


@app.route('/track')
@flask_cors.cross_origin(origins=mt.get_allowed_origins())
def track():
    return mt.track()


@app.route("/favicon.ico")  # Load the favicon
def fav():
    return send_from_directory(app.static_folder, 'favicon.ico')


# Main
if __name__ == '__main__':
    host = '0.0.0.0'
    port = 3033

    if os.getenv('STAGE', False) == 'dev':
        app.run(host=host, port=port, debug=True)
    else:
        waitress.serve(app, host=host, port=port)
