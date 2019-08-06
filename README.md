# Helsinki city bikes Alexa skill

Amazon lambda function for handling Helsinki city bikes Alexa skill requests.

Install skill from [Alexa skills store](https://www.amazon.com/dp/B07VY1Y7V1/)

## Usage

Activate skill by one of following:

> Alexa, open city bikes

> Alexa, ask city bikes is there bikes near by 

Skill needs access to device address for finding closest bike station. Allow permissions when installing or after first skill activation.

## Quick setup

Get your own skill handler 

```bash
$ git clone ...
$ python -m venv env
$ source env/bin/activate
$ pip pip install -r requirements.txt
```

Set enviroment variable `ALEXA_APPLICATION_ID` to your app id from Alexa developer console.

Code is tested on Python 3.7

See [Amazon documentation](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python-how-to-create-deployment-package.html#python-package-dependencies) for deploying function to AWS.

## Built with
* [HSL api]() public api to access city bike station data
* [geopy](https://github.com/geopy/geopy) for geocoding address and distance calulation