<%inherit file="_templates/site.mako" />

<p>Path: ${breadcrumbs}</p>

% for photo in photos:
  <a href="${photo['photo']}.html"><img src="${photo['thumb']}" class="thumbnail" alt="${photo['photo']}" /></a>
% endfor

% if caption:
  ${caption}
% endif

<%namespace name="externalcode" file="externalcode.mako"/>
${externalcode.disquscomments(indexurl)}
