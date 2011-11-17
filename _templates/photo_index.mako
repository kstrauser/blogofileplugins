<%inherit file="_templates/site.mako" />

<p>Path: ${breadcrumbs}</p>

% for photo in photos:
  <a href="${photo['original']}.html"><img src="${photo['thumb']}" class="thumbnail" alt="${photo['original']}" /></a>
% endfor

% if caption:
  ${caption}
% endif

<%namespace name="extdisqus" file="extdisqus.mako"/>
${extdisqus.disquscomments(indexurl, slug)}
