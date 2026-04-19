# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2015 bendikro bro.devel+yarss2@gmail.com
#
# This file is part of YaRSS2 and is licensed under GNU General Public License 3.0, or later, with
# the additional special exception to link portions of this program with the OpenSSL library.
# See LICENSE for more details.
#

import re
import smtplib

from twisted.internet import threads

from yarss2.util import logging

# Mime (might) not be included with Deluge on Windows.
try:
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
except ImportError:
    # These must be readded if required
    from yarss2.lib.mime.multipart import MIMEMultipart
    from yarss2.lib.mime.text import MIMEText


log = logging.getLogger(__name__)


def send_email(email_conf, server_conf):
    """sends email notification of finished torrent"""
    # Send multipart message with text and html
    if "message" in email_conf:
        # Send Multipart email
        if "message_html" in email_conf:
            mime_message = MIMEMultipart("alternative")
            msg_plain = MIMEText(email_conf["message"].encode('utf-8'), "plain", _charset='utf-8')
            msg_html = MIMEText(email_conf["message_html"].encode('utf-8'), "html", _charset='utf-8')
            mime_message.attach(msg_plain)
            mime_message.attach(msg_html)
        else:
            # Send plain message
            mime_message = MIMEText(email_conf["message"].encode('utf-8'), "plain", _charset='utf-8')
    elif "message_html" in email_conf:
        # Send html message
        mime_message = MIMEText(email_conf["message"].encode('utf-8'), "html", _charset='utf-8')
    else:
        log.warn("Email config must contain either 'message' or 'message_html'")
        return False

    mime_message["Subject"] = email_conf["subject"]
    mime_message["From"] = server_conf["from_address"]
    mime_message["To"] = email_conf["to_address"]

    port = smtplib.SMTP_PORT
    if len(server_conf["smtp_port"].strip()) > 0:
        try:
            port = int(server_conf["smtp_port"])
        except ValueError:
            pass
    try:
        mail_server = smtplib.SMTP(server_conf["smtp_server"], port)
    except Exception as e:
        log.error("There was an error sending the notification email: %s" % e)
        return False

    log.info("Sending email message:\nTo: %s\nFrom: %s\nSubject: %s\n" %
             (mime_message["To"], mime_message["From"], mime_message["Subject"]))
    log.info("Server: %s, port: %s, authentication: %s" % (server_conf["smtp_server"],
                                                           server_conf["smtp_port"],
                                                           server_conf["smtp_authentication"]))
    if server_conf["smtp_authentication"]:
        mail_server.ehlo()
        mail_server.starttls()
        mail_server.ehlo()
        try:
            mail_server.login(server_conf["smtp_username"], server_conf["smtp_password"])
        except smtplib.SMTPHeloError:
            log.warn("The server didn't reply properly to the helo greeting")
        except smtplib.SMTPAuthenticationError:
            log.warn("The server didn't accept the username/password combination")
    try:
        mail_server.sendmail(server_conf["from_address"], email_conf["to_address"], mime_message.as_string())
        mail_server.quit()
    except Exception as e:
        log.error("Sending email notification failed: %s" % e)
        return False
    else:
        log.info("Sending email notification of finished torrent was successful")
    return True


def send_torrent_email(email_configurations, email_msg, subscription_data=None,
                       torrent_name_list=None, deferred=False, callback_func=None, email_data={}):
    """Send email with optional list of torrents
    Arguments:
    email_configurations - the main email configuration of YARSS2
    email_msg - a dictionary with the email data (as saved in the YARSS config)
    torrents - a tuple containing the subscription data and a list of torrent names.
    """
    log.info("Sending email '%s'" % email_msg["name"])
    email_data["to_address"] = email_msg["to_address"]
    email_data["subject"] = email_msg["subject"]
    email_data["message"] = email_msg["message"]

    if email_data["message"].find("$subscription_title") != -1 and subscription_data:
        email_data["message"] = email_data["message"].replace("$subscription_title", subscription_data["name"])

    if email_data["subject"].find("$subscription_title") != -1 and subscription_data:
        email_data["subject"] = email_data["subject"].replace("$subscription_title", subscription_data["name"])

    if email_data["message"].find("$torrentlist") != -1 and torrent_name_list:
        torrentlist_plain = " * %s\n" % "\n * ".join(f for f in torrent_name_list)
        msg_plain = email_data["message"].replace("$torrentlist", torrentlist_plain)
        torrentlist_html = "<ul><li>%s </li></ul>" % \
            "</li> \n <li> ".join(f for f in torrent_name_list)
        msg_html = email_data["message"].replace('\n', '<br/>')
        msg_html = re.sub(r'\$torrentlist(<br/>){1}?', torrentlist_html, msg_html)
        email_data["message"] = msg_plain
        email_data["message_html"] = msg_html

    # Send email with twisted to avoid waiting
    if deferred:
        d = threads.deferToThread(send_email, email_data, email_configurations)
        if callback_func is not None:
            d.addCallback(callback_func)
        return d
    else:
        return send_email(email_data, email_configurations)
