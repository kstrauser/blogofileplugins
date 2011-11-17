<%inherit file="_templates/site.mako" />

<p>Path: ${breadcrumbs}</p>

<a href="${original}"><img src="${medium}" class="photo" alt="${photourl}" /></a>

% if caption:
  ${caption}
% endif

<%namespace name="extdisqus" file="extdisqus.mako"/>
${extdisqus.disquscomments(photourl, slug)}
