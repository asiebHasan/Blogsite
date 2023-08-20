from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.contrib.postgres.search import TrigramSimilarity

from .models import Post, Comment
from .forms import CommentForm, SearchForm

from taggit.models import Tag
from django.db.models import Count

# Create your views here.


def post_list(request, tag_slug=None):
    object_list = Post.published.all()
    tag = None
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        object_list = object_list.filter(tags__name__in=[tag])

    paginator = Paginator(object_list, 3)
    page = request.GET.get('page')
    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        posts = paginator.page(1)
    except EmptyPage:
        posts = paginator.page(paginator.num_pages)

    return render(request, 'blog/post/list.html', {'page': page, 'posts': posts, 'tag': tag})


def post_detail(request, year, month, day, post):
    post = get_object_or_404(Post, slug=post, status='published',
                             publish__year=year, publish__month=month, publish__day=day)

    comments = post.comments.filter(active=True)  # type: ignore
    new_comment = None

    if request.method == 'POST':
        comment_form = CommentForm(data=request.POST)
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.post = post
            new_comment.save()
    else:
        comment_form = CommentForm()

    # List of similar posts
    post_tags_ids = post.tags.values_list('id', flat=True)
    similar_posts = Post.published.filter(
        tags__id__in=post_tags_ids).exclude(id=post.id)  # type: ignore

    similar_posts = similar_posts.annotate(same_tags=Count(
        'tags')).order_by('-same_tags', '-publish')[:4]

    return render(request, 'blog/post/detail.html', {
        'post': post,
        'comments': comments,
        'new_comments': new_comment,
        'comment_form': comment_form,
        'similar_posts': similar_posts
    })


def post_search(request):
    query = None
    results = []

    if 'query' in request.GET:
        query = request.GET.get('query')
        if query:
            search_vector = SearchVector(
                'title', weight='A') + SearchVector('body', weight='B')
            search_query = SearchQuery(query)
            # results = Post.published.annotate(
            #     search=search_vector,
            #     rank=SearchRank(
            #         search_vector, search_query)).filter(rank__gte=0.3).order_by('-rank')

            # TrigramSimilarity applied
            results = Post.published.annotate(
                similarity=TrigramSimilarity(
                    'title', query) + TrigramSimilarity('body', query)
            ).filter(similarity__gte=0.1).order_by('-similarity')

    return render(request, 'blog/post/search.html', {
        'query': query,
        'results': results
    })
