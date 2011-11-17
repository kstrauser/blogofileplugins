<%def name="disquscomments(pageurl, slug=None)">
% if bf.config.blog.disqus.enabled:
<div>
<div id="disqus_thread"></div>
<script type="text/javascript">
    var disqus_shortname = '${bf.config.blog.disqus.name}';
% if slug:
    var disqus_identifier = '${slug}';
% endif
    (function() {
        var dsq = document.createElement('script'); dsq.type = 'text/javascript'; dsq.async = true;
        dsq.src = 'http://' + disqus_shortname + '.disqus.com/embed.js';
        (document.getElementsByTagName('head')[0] || document.getElementsByTagName('body')[0]).appendChild(dsq);
    })();
</script>
<noscript><p>Please enable JavaScript to view the <a href="http://disqus.com/?ref_noscript">comments powered by Disqus.</a></p></noscript>
<a href="http://disqus.com" class="dsq-brlink">blog comments powered by <span class="logo-disqus">Disqus</span></a>
</div>
% endif
</%def>
