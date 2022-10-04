# MiniTracker

A simple Python-based click tracker

## Description

MiniTracker takes a URL, parses requested parameters, and sends them off as metrics to Graphite TSDB 

## Getting Started

### Dependencies

For Python dependencies, see `requirements.txt`.

You also need to set up a graphite server.
For easy testing and/or deployment, use the following docker containers:
- [graphiteapp/graphite-statsd](https://hub.docker.com/r/graphiteapp/graphite-statsd)

### Installing

- Clone this repository
```
git clone git@github.com:unfoldingWord-dev/minitracker
cd 
pip install -r requirements.txt
```

- Or pull the docker container from [here](https://hub.docker.com/r/unfoldingword/cloudfront_logprocessor)
```
docker pull unfoldingword/minitracker
```

- Or build your own docker container with the help of the provided Dockerfile
```
docker build -t <dockerhub-username>/<repo-name> .
```

### Executing program
#### Running the python program
```
python path/to/repository/main.py
```

#### Running as a docker container
```
docker run --env-file .env --rm -p 3033:3033 --name minitracker unfoldingword/minitracker
```

You need to provide the following environment variables, 
either through a .env file, or by setting them manually

- `GRAPHITE_HOST` *(Your graphite host, to send metrics to. E.g. `localhost`)*
- `GRAPHITE_PREFIX` *(Prefix for all graphite entries. E.g. `obs.website.downloads`)*
- `STAGE` (Are you running on `dev` or `prod`?)\
On `dev`, we are quite verbose with logging, and we are running on the internal web server

## Authors

- [yakob-aleksandrovich ](https://github.com/yakob-aleksandrovich)

## Version History

* 0.1
    * Initial Release

## License

This project is licensed under the MIT License