<%inherit file="_templates/site.mako" />

<p>Path: ${breadcrumbs}</p>

<img src="${photo['photo']}" class="photo" alt="${photourl}" />

% if photo['caption']:
  ${photo['caption']}
% endif

<%namespace name="externalcode" file="externalcode.mako"/>
${externalcode.disquscomments(photourl)}
