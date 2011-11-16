<%inherit file="_templates/site.mako" />

<p>Path: ${breadcrumbs}</p>

<h2>Albums</h2>

<div class="clear-block">
% for dir in dirs:
<div class="gallery"><a href="${dir[0]}"><img src="${dir[0]}/showcase.jpg" alt="${dir[0]} gallery" class="thumbnail" /></a>${dir[1]}</div>
% endfor
</div>

% if caption:
  ${caption}
% endif

<%namespace name="externalcode" file="externalcode.mako"/>
${externalcode.disquscomments(indexurl)}
