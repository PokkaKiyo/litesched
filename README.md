# litesched

A sample project for *learning* how to:
1. Set up a litestar asgi app
2. Integrate APScheduler into the app
3. Various admin port options, with mutual TLS auth, to update the scheduler at runtime

And some other stuff:
- Sending a favicon 🤷‍♀️ from a backend endpoint
- Logging configuration in litestar

On the topic of admin ports, there are a number of ways to do this.
The example provides 3 admin port options:
- TCP Socket
- Unix Socket
- Unix Abstract Socket

These sockets are wrapped with an SSL context that requires mutual TLS authentication. Note that 1 way TLS doesn't make sense, the client needs to be authenticated, else anyone can update the scheduler.

The cli directory contains 3 scripts, each only slightly different for interacting with their respective servers.

To try the example, create a self signed certificate:
```shell
openssl req -new -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout key.pem -out cert.pem \
  -subj "/CN=127.0.0.1/O=Development Certificate" \
  -addext "subjectAltName=IP:127.0.0.1"
```

Other ways not currently implemented:
- Mutual TLS isn't the only way, an unencrypted way of just using a challenge, password, or token to verify trustworthiness of other side can work, although communication won't be encrypted
- Use an API endpoint, with some session or token authentication, which allows the admin command to be accessed via both HTTP API calls and via command line with a HTTP call wrapper, e.g. curl or httpx
