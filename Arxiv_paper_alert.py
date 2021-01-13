"""
Adapted from
http://arxiv.org/help/api/examples/python_arXiv_parsing_example.txt

with modifications by Alex Breitweiser; Aurélien Dersy for V2

This is free software.  Feel free to do what you want
with it, but please play nice with the arXiv API!
"""

import time
from urllib import request
import feedparser
from datetime import date, timedelta
from smtplib import SMTP
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email_credentials import personal_mail, mail_password

#
send_email = True

# Choice of category

category_options = [["hep-ph", {"cs.AI", "cs.CL", "cs.IR", "cs.LG", "cs.NE", "physics.comp-ph"}],
                    ["physics.comp-ph", {"cs.AI", "cs.CL", "cs.IR", "cs.LG", "cs.NE", "hep-ph", "hep-th"}],
                    ["cs.LG", {"hep-ph", "hep-th", "physics.comp-ph"}],
                    ["cs.AI", {"hep-ph", "hep-th", "physics.comp-ph"}],
                    ]

for category in category_options:

    # Recover category structure
    base_cat = category[0]
    cross_cats = category[1]

    # Base api query url
    base_url = 'http://export.arxiv.org/api/query?'

    # Search parameters
    days_ago = 5
    today = date.today()
    days_ago_limit = today - timedelta(days_ago)
    start_date = days_ago_limit.strftime("%Y%m%d")+"2000"
    end_date = today.strftime("%Y%m%d") + "2000"
    search_query = 'cat:%s+AND+lastUpdatedDate:[%s+TO+%s]' % (base_cat, start_date, end_date)
    start = 0                     # retrieve the first 5 results
    max_results = 100

    query = 'search_query=%s&start=%i&max_results=%i' % (search_query,
                                                         start,
                                                         max_results)

    # Opensearch metadata such as totalResults, startIndex,
    # and itemsPerPage live in the opensearch namespace.
    # Some entry metadata lives in the arXiv namespace.
    # This is a hack to expose both of these namespaces in
    # feedparser v4.1
    # noinspection PyProtectedMember
    feedparser._FeedParserMixin.namespaces['http://a9.com/-/spec/opensearch/1.1/'] = 'opensearch'
    # noinspection PyProtectedMember
    feedparser._FeedParserMixin.namespaces['http://arxiv.org/schemas/atom'] = 'arxiv'

    # perform a GET request using the base_url and query
    response = request.urlopen(base_url+query).read()

    # parse the response using feedparser
    feed = feedparser.parse(response)

    title = "New %s submissions cross listed on %s" % (base_cat, ", ".join(cross_cats))

    body = "<h1>%s</h1>" % title

    body += 'Feed last updated: %s' % feed.feed.updated

    # Run through each entry, and print out information
    for entry in feed.entries:

        print(entry.author_detail['name'])
        all_categories = [t['term'] for t in entry.tags]
        if not any(cat in cross_cats for cat in all_categories):
            continue
        arxiv_id = entry.id.split('/abs/')[-1]
        if arxiv_id[-2:] != 'v1':
            continue
        pdf_link = ''
        for link in entry.links:
            if link.rel == 'alternate':
                continue
            elif link.title == 'pdf':
                pdf_link = link.href
        body += '<a href="%s"><h2>%s</h2></a>' % (pdf_link, entry.title)

        # feedparser v5.0.1 correctly handles multiple authors, print them all
        try:
            body += 'Authors:  %s</br>' % ', '.join(author.name for author in entry.authors)
        except AttributeError:
            pass

        try:
            comment = entry.arxiv_comment
        except AttributeError:
            comment = 'No comment found'
        body += 'Comments: %s</br>' % comment

        # Since the <arxiv:primary_category> element has no data, only
        # attributes, feedparser does not store anything inside
        # entry.arxiv_primary_category
        # This is a dirty hack to get the primary_category, just take the
        # first element in entry.tags.  If anyone knows a better way to do
        # this, please email the list!
        body += 'Primary Category: %s</br>' % entry.tags[0]['term']

        # Lets get all the categories
        all_categories = [t['term'] for t in entry.tags]
        body += 'All Categories: %s</br>' % ', '.join(all_categories)

        # The abstract is in the <summary> element
        body += '<p>%s</p>' % entry.summary
        body += '</br>'
    print(body)

    if send_email:

        msg = MIMEMultipart()
        msg['Subject'] = title
        msg['From'] = personal_mail
        msg['To'] = personal_mail
        msg.attach(MIMEText(body, 'html'))

        server = SMTP("smtp.gmail.com:587")
        server.ehlo()
        server.starttls()
        server.login(personal_mail, mail_password)
        server.sendmail(msg['From'],  msg['To'], msg.as_string())

    # Pause for 5 sec to be nice to the arxiv server
    time.sleep(5)
