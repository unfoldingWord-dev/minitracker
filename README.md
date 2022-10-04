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

### Setup behind proxy
The following is a basic 'Nginx as proxy' configuration
```nginx
# Set rate limiting at 5 requests per second per IP address
limit_req_zone $binary_remote_addr zone=log_limit:10m rate=5r/s;

server {
    listen 80;

    server_name <your server>;

    access_log  /var/log/nginx/access.log main;
    error_log  /var/log/nginx/error.log main;

    location / {
            proxy_pass         http://minitracker:3033/;
            proxy_redirect     off;
    
            proxy_set_header   Host                 $host;
            proxy_set_header   X-Real-IP            $remote_addr;
            proxy_set_header   X-Forwarded-For      $proxy_add_x_forwarded_for;
            proxy_set_header   X-Forwarded-Proto    $scheme;
        }
    
    location /log/downloads {
        # Enable rate limiting
        limit_req zone=log_limit;
    
        # Proxy to MiniTracker
        proxy_pass         http://minitracker:3033;
        proxy_redirect     off;
    
        proxy_set_header   Host                 $host;
        proxy_set_header   X-Real-IP            $remote_addr;
        proxy_set_header   X-Forwarded-For      $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto    $scheme;
    
        # Keep logs
        access_log  /var/log/nginx/$host-downloads.log main;
    
        # CORS requests allowed
        add_header 'Access-Control-Allow-Origin' 'https://www.openbiblestories.org/' always;
        add_header 'Vary' 'Origin';
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, OPTIONS';
        add_header 'Access-Control-Allow-Headers' 'Authorization,DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range';
        add_header 'Access-Control-Expose-Headers' 'Content-Length,Content-Range';
        if ($request_method = 'OPTIONS') {
           add_header 'Access-Control-Allow-Origin' 'https://www.openbiblestories.org/' always;
           add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, OPTIONS';
           add_header 'Access-Control-Allow-Headers' 'Authorization,DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range';
           add_header 'Access-Control-Max-Age' 1728000; # 20 days
           add_header 'Content-Type' 'text/plain; charset=utf-8';
           add_header 'Content-Length' 0;
           return 204;
        }
    }
}
```


## Authors

- [yakob-aleksandrovich ](https://github.com/yakob-aleksandrovich)

## Version History

* 0.1
    * Initial Release

## License

This project is licensed under the MIT License