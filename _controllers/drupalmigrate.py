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
    'rulefile': 'rewriterules.txt',
    # Include a special pattern to serve the site's root index with Blogofile.
    # If this is true, you need to provide an index.html page (as the
    # simple_blog setup does this by default).
    'includeindex': True,

    # Whether to generate a list of unconverted Drupal nodes
    'makeindex': True,
    # Relative to the blog directory
    'indexfile': 'drupalindex.mako',
    # The types of Drupal nodes to include in the index
    'nodetypes': ('acidfree', 'blog', 'page', 'story'),
    # The Location of Drupal within your website (eg, is it under /drupal?).
    # Analogous to blog.path.
    'drupalpath': '/',
    # Drupal's database connection settings
    'host': 'localhost',
    'user': 'foo',
    'passwd': 'passwd',
    'db': 'drupaldb',
}

MODULELOG = logging.getLogger(__name__)
MODULELOG.setLevel(logging.INFO)

CONFIG = bf.config.controllers.drupalmigrate


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
    if CONFIG.makeindex:
        makeindex()


def makeindex():
    """Build an index of all interesting nodes from the Drupal site

    This connects to your Drupal site's MySQL database, downloads a list of
    nodes, and creates a static list of links to those nodes. Just <%include />
    it in your site's profile page.
    """

    dbconn = MySQLdb.connect(host=CONFIG.host, user=CONFIG.user, passwd=CONFIG.passwd, db=CONFIG.db)
    cursor = dbconn.cursor()
    cursor.execute("""\
SELECT
    created,
    dst,
    nid,
    title,
    type
FROM
    node
    LEFT JOIN url_alias ON url_alias.src = CONCAT('node/', node.nid)
WHERE
    type IN (%s) AND
    status = 1
ORDER BY created DESC""" % ', '.join(repr(MySQLdb.escape_string(nodetype))
                                     for nodetype in CONFIG.nodetypes))
    fields = [field[0] for field in cursor.description]

    # Get a set of permalinks to Blogofile posts in the same format as Drupal's
    # permalinks.
    currentblogs = {urlparse.urlparse(post.permalink).path.lstrip('/')  # pylint: disable=E1101
                    for post in bf.config.blog.posts}
    linkcount = 0
    seennodes = set()
    with open(CONFIG.indexfile, 'w') as indexfile:
        indexfile.write('<ul>\n')
        for row in cursor.fetchall():
            row = dict(zip(fields, row))
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
                permalink = dst
            else:
                permalink = '/'.join(thisnode)

            # Once we've migrated a node to Blogofile, remove it from the
            # legacy index.
            if permalink in currentblogs:
                MODULELOG.info('Skipping %s', permalink)
                continue

            indexfile.write(
                '<li><h2 class="title"><a href="%s%s">%s</a></h2>'
                '<span class="submitted">%s</span></li>\n' % (
                CONFIG.drupalpath,
                permalink,
                title,
                datetime.datetime.fromtimestamp(row['created']) \
                    .strftime("%B %d, %Y at %I:%M %p")))
            linkcount += 1
        indexfile.write('</ul>')
    MODULELOG.info('Wrote %s links', linkcount)


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

    with open(CONFIG.rulefile, 'w') as rulefile:
        if CONFIG.includeindex:
            rulefile.write(ruletemplate % ('', '$'))
        for path in sorted(glob.glob('_site/*')):
            if os.path.isdir(path):
                patternending = '(/|$)'
            else:
                patternending = '$'
            rulefile.write(ruletemplate % (os.path.basename(path), patternending))
