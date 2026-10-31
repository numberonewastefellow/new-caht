"""Webhook triggers: an outside system starts a workflow with a signed HTTP call.

tokens   the URL token and signing secret
verify   proving who is calling, one verifier per auth mode
limits   rate limits and the client address, before any database work
payload  checking the body, removing credentials, and rendering it as untrusted text
intake   the request steps in order, with no HTTP framework types
listen   Listen mode: capture a test call for the owner without running anything
"""
