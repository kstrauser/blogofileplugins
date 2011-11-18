<%inherit file="_templates/site.mako" />

<p>Path: ${breadcrumbs}</p>

<h2>Albums</h2>

<div class="clear-block">
% for subdir in subdirs:
	<div class="gallery">
		<div class="galleryimage">
			<a href="${subdir['name']}/"><img src="${subdir['name']}/showcase.jpg" alt="${subdir['name']} gallery" class="thumbnail" /></a>
		</div>
% if subdir['caption']:
		<div class="gallerycaption">${subdir['caption']}</div>
% endif
	</div>
% endfor
</div>

% if caption:
${caption}
% endif

<%namespace name="extdisqus" file="extdisqus.mako"/>
${extdisqus.disquscomments(indexurl, slug)}
