<%inherit file="_templates/site.mako" />

<p>Path: ${breadcrumbs}</p>

<h2>Photos</h2>

<div class="clear-block">
% for photo in photos:
	<div class="gallery">
		<div class="galleryimage">
			<a href="${photo['original']}.html"><img src="${photo['thumb']}" class="thumbnail" alt="${photo['original']}" /></a>
		</div>
% if photo['caption']:
		<div class="gallerycaption">${photo['caption']}</div>
% endif
	</div>
% endfor
</div>

% if caption:
${caption}
% endif

<%namespace name="extdisqus" file="extdisqus.mako"/>
${extdisqus.disquscomments(indexurl, slug)}
