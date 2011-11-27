#!/usr/bin/env python

"""Controller to ease migration from Drupal to Blogofile

With this setup, you can leave your Drupal site in place and gradually convert
your old Drupal nodes into Blogofile posts. If you make your Blogofile theme
similar enough, your visitors never have to notice that you've made the
switch.

More creatively, you can use this system as a Drupal accelerator. If you have
a few articles on a busy site that are responsible for most of your traffic,
you can overlay Blogofile onto Drupal so that those pages are served as static
files.
"""

import datetime
import glob
import logging
import os
import urlparse

import MySQLdb

from blogofile.cache import bf

config = {  # pylint: disable=C0103
    'name': 'Apache RewriteRule exceptions',
    'description': 'Generate a list of pages not to pass through to the old blog',
    'author': 'Kirk Strauser <kirk@strauser.com>',
    'url': 'https://github.com/kstrauser/blogofile/blob/master/blogofile/site_init'
           '/blog_controller/_controllers/drupalmigrate.py',

    # Whether to generate Apache RewriteRules to skip Blogofile posts
    'makerewriterules': True,
    # Relative to the blog directory
    'exceptionrulefile': 'exceptionrewriterules.txt',
    # Include a special pattern to serve the site's root index with Blogofile.
    # If this is true, you need to provide an index.html page (as the
    # simple_blog setup does this by default).
    'includeindex': True,

    # Whether to generate a list of unconverted Drupal nodes
    'makeindex': True,
    # Relative to the blog directory
    'indexfile': 'drupalindex.mako',
    # The types of Drupal nodes to include in the index
    'indexnodetypes': ('acidfree', 'blog', 'page', 'story'),
    # The Location of Drupal within your website (eg, is it under /drupal?).
    # Analogous to blog.path.
    'drupalpath': '/',
    # Drupal's database connection settings
    'host': 'localhost',
    'user': 'foo',
    'passwd': 'passwd',
    'db': 'drupaldb',

    # Whether to create a set of posts from Drupal nodes
    'makeposts': False,
    # The serial number the number of the first post to generate
    'startpostnum': 100,
    # The types of Drupal nodes to convert to Blogofile posts
    'convertnodetypes': ('blog', 'page', 'story'),
    # The username of the primary Drupal blogger. Other usernames will get
    # "Guest post" titles.
    'mainusername': 'admin',

    # Whether to make a list of redirects from old Drupal permalinks to new
    # Blogofile permalinks
    'makepermalinkredirs': False,
    # Relative to the blog directory
    'redirectrulefile': 'redirectrewriterules.txt',
}

MODULELOG = logging.getLogger(__name__)
MODULELOG.setLevel(logging.INFO)

CONFIG = bf.config.controllers.drupalmigrate

SQL = {
    'getnodes': """\
SELECT
    node.created,
    url_alias.dst,
    node.nid,
    node.title,
    node.type,
    node_revisions.body,
    node_revisions.teaser,
    users.name AS username
FROM
    node
    LEFT JOIN url_alias ON url_alias.src = CONCAT('node/', node.nid)
    JOIN node_revisions ON node.nid = node_revisions.nid
    JOIN users ON node.uid = users.uid
WHERE
    node.status = 1
ORDER BY created DESC""",

    'getnodetags': """\
SELECT
    name
FROM
    term_node
    JOIN term_data ON term_node.tid = term_data.tid
WHERE
    term_node.nid = %s""",
}


def init():
    """Call makerewriterules() after the rest of the site is build, if configured"""
    if not CONFIG.enabled:
        return
    oldpostbuild = bf.config.post_build

    def post_build_makerewriterules():
        """Call the current post_build function, then our new one"""
        oldpostbuild()
        makerewriterules()

    if CONFIG.makerewriterules:
        bf.config.post_build = post_build_makerewriterules


def run():
    """Execute all the requested migration actions"""
    if CONFIG.makeindex or CONFIG.makeposts:
        transformnodes()
    if CONFIG.makepermalinkredirs:
        makepermalinkredirs()


def makepermalinkredirs():
    """Make a set of RewriteRules so that posts created from old Drupal nodes
    (eg by 'makeposts') get redirects from their old permalinks to their new
    locations"""
    MODULELOG.info('Making permalink redirects')
    siteurl = bf.config.site.url
    stripcount = len(siteurl)
    if siteurl.endswith('/'):
        stripcount -= 1
    with open(CONFIG.redirectrulefile, 'w') as rulefile:
        for post in bf.config.blog.posts:
            try:
                drupalpermalink = post.drupalpermalink
            except AttributeError:
                continue
            permalink = post.permalink
            if not permalink.startswith(siteurl):
                raise Exception('Bad permalink: %s' % permalink)
            if not drupalpermalink.startswith(siteurl):
                raise Exception('Bad drupalpermalink: %s' % drupalpermalink)
            permalink = permalink[stripcount:]
            drupalpermalink = drupalpermalink[stripcount:].rstrip('/')
            rulefile.write('\tRewriteRule ^%s(/|$) %s [R=301,L]\n' % (drupalpermalink, permalink))


def makerewriterules():
    """Make a set of RewriteRules so no Blogofile files are passed through to Drupal

    From my Apache virtual domain config:

        DirectoryIndex index.html

        # This is the file named in config['rulefile']
        Include /usr/local/www/htdocs/site.example.com/mysite/_site/rewriterules.txt

        # Everything else is served by Drupal
        RewriteRule ^/?(.*)$ http://site.example.com/$1 [P,L]

    """

    MODULELOG.info('Making RewriteRules')

    ruletemplate = 'RewriteRule ^/%s%s - [L]\n'

    with open(CONFIG.exceptionrulefile, 'w') as rulefile:
        if CONFIG.includeindex:
            rulefile.write(ruletemplate % ('', '$'))
        for path in sorted(glob.glob('_site/*')):
            if os.path.isdir(path):
                patternending = '(/|$)'
            else:
                patternending = '$'
            rulefile.write(ruletemplate % (os.path.basename(path), patternending))


def transformnodes():
    """Build an index of all interesting nodes from the Drupal site or create
    Blogofile posts from them

    This connects to your Drupal site's MySQL database, downloads a list of
    nodes, and creates a static list of links to those nodes. Just <%include />
    it in your site's profile page.
    """

    dbconn = MySQLdb.connect(host=CONFIG.host, user=CONFIG.user, passwd=CONFIG.passwd, db=CONFIG.db)
    cursor = dbconn.cursor()
    cursor.execute(SQL['getnodes'])
    fields = [field[0] for field in cursor.description]
    nodes = [dict(zip(fields, row)) for row in cursor.fetchall()]

    # Get a set of permalinks to Blogofile posts in the same format as Drupal's
    # permalinks.
    currentblogs = {urlparse.urlparse(post.permalink).path.strip('/')  # pylint: disable=E1101
                    for post in bf.config.blog.posts}
    linkcount = 0
    postcount = 0
    seennodes = set()

    if CONFIG.makeindex:
        indexfile = open(CONFIG.indexfile, 'w')
        indexfile.write('<ul>\n')

    for row in nodes:
        thisnode = (row['type'], row['nid'])

        # Only generate one link to a given node
        if thisnode in seennodes:
            continue
        seennodes.add(thisnode)

        try:
            dst = unicode(row['dst'])
            title = unicode(row['title'])
        except UnicodeDecodeError:
            continue

        # Use Pathauto's permalink, if available. Otherwise use the
        # standard Drupal node link
        if dst:
            slug = dst.strip('/')
        else:
            slug = '/'.join(thisnode)
        permalink = bf.config.site.url + slug + '/'

        if CONFIG.makeindex and row['type'] in CONFIG.indexnodetypes \
              and not slug in currentblogs:
            indexfile.write(
                '<li><a href="%s%s">%s</a> '
                '<span class="submitted">%s</span></li>\n' % (
                CONFIG.drupalpath,
                slug,
                title,
                datetime.datetime.fromtimestamp(row['created']) \
                    .strftime("%B %d, %Y at %I:%M %p")))
            linkcount += 1

        if CONFIG.makeposts and row['type'] in CONFIG.convertnodetypes:
            cursor.execute(SQL['getnodetags'], row['nid'])
            tags = [tag[0] for tag in cursor.fetchall()]

            if row['username'] != CONFIG.mainusername:
                title = 'Guest post by %s: %s' % (row['username'], title)
                tags.append(row['username'])

            with open('_posts/%03d - %s.markdown' % (
                  CONFIG.startpostnum + postcount,
                  slug), 'wb') as postfile:
                postfile.write("""\
---
categories: %(tags)s
date: %(date)s
title: '%(title)s'
drupalpermalink: %(permalink)s
drupalslug: %(slug)s
---
%(body)s
""" % {
    'body': row['body'].replace('\r\n', '\n'),
    'date': datetime.datetime.fromtimestamp(row['created']) \
                    .strftime("%Y/%m/%d %H:%M:%S"),
    'permalink': permalink,
    'slug': slug,
    'tags': ', '.join(sorted(tags)),
    'title': title.replace("'", "''"),
})
            postcount += 1

    if CONFIG.makeindex:
        indexfile.write('</ul>')
        indexfile.close()
        MODULELOG.info('Wrote %s links', linkcount)
    if CONFIG.makeposts:
        MODULELOG.info('Wrote %s posts', postcount)
