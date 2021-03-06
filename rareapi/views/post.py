"""View module for handling requests about posts"""
from rareapi.views.author import AuthorSerializer
from django.db.models.fields.related import ManyToManyField
from rest_framework.decorators import action
from rareapi.models.comment import Comment
from django.core.exceptions import ValidationError
from django.http import HttpResponseServerError, request
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import serializers
from rest_framework import status
from django.contrib.auth.models import User  # pylint:disable=imported-auth-user
from rareapi.models import Post, Category, Author, author
from django.core.files.base import ContentFile
import base64
import uuid


class AuthorSerializer(serializers.ModelSerializer):
    """JSON serializer for event organizer"""

    class Meta:
        model = Author
        fields = ['id', 'profile_image_url', 'created_on', 'active', 'bio']
        depth = 1

class UserSerializer(serializers.ModelSerializer):
    """JSON serializer for event host's related Django user"""
    author = AuthorSerializer(many=False)
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'id', 'author')

class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False)
    isAuthor = serializers.SerializerMethodField()

    def get_isAuthor(self, object):
        return self.context['request'].auth.user == object.user

    class Meta:
        model = Comment
        fields = ('content', 'user', 'created_on', 'isAuthor', 'id')

class PostSerializer(serializers.ModelSerializer):
    """JSON serializer for posts

    Arguments:
        serializer type
    """
    is_post_author = serializers.SerializerMethodField()
    def get_is_post_author(self, object):
        return self.context["request"].auth.user == object.user
    user = UserSerializer(many=False)
    comments = CommentSerializer(many=True)
    
    class Meta:
        model = Post
        fields = ('id', 'title', 'content', 'publication_date',
                  'image_url', 'approved', 'category', 'tags', 'user', 'comments', 'is_post_author' )
        depth = 2


class PostView(ViewSet):
    """Level up posts"""

    def create(self, request):
        """Handle POST operations

        Returns:
            Response -- JSON serialized post instance
        """

        # Uses the token passed in the `Authorization` header
        user = User.objects.get(username=request.auth.user)

        # Create a new Python instance of the Post class
        # and set its properties from what was sent in the
        # body of the request from the client.
        post = Post()
        post.user = user
        post.title = request.data["title"]
        post.publication_date = request.data["publication_date"]
        format, imgstr = request.data["image_url"].split(';base64,')
        ext = format.split('/')[-1]
        data = ContentFile(base64.b64decode(imgstr), name=f'{request.data["title"]}-{uuid.uuid4()}.{ext}')
        post.image_url = data
        post.content = request.data["content"]
        post.approved = request.data["approved"]

        # Use the Django ORM to get the record from the database
        # whose `id` is what the client passed as the
        # `postTypeId` in the body of the request.

        category = Category.objects.get(pk=request.data["category_id"])
        post.category = category

        # Try to save the new post to the database, then
        # serialize the post instance as JSON, and send the
        # JSON as a response to the client request
        try:
            post.save()
            post.tags.set(request.data["tags"])
            serializer = PostSerializer(post, context={'request': request})
            return Response(serializer.data)

        # If anything went wrong, catch the exception and
        # send a response with a 400 status code to tell the
        # client that something was wrong with its request data
        except ValidationError as ex:
            return Response({"reason": ex.message}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        """Handle GET requests for single post

        Returns:
            Response -- JSON serialized post instance
        """
        try:
            # `pk` is a parameter to this function, and
            # Django parses it from the URL route parameter
            #   http://localhost:8000/posts/2
            #
            # The `2` at the end of the route becomes `pk`

            post = Post.objects.get(pk=pk)

            serializer = PostSerializer(post, context={'request': request})
            return Response(serializer.data)
        except Exception as ex:
            return HttpResponseServerError(ex)

    def update(self, request, pk=None):
        """Handle PUT requests for a post

        Returns:
            Response -- Empty body with 204 status code
        """
        post = Post.objects.get(pk=pk)

        # Do mostly the same thing as POST, but instead of
        # creating a new instance of Post, get the post record
        # from the database whose primary key is `pk`
        # Via query params, PK becomes whatever ID is passed through the param
        post = Post.objects.get(pk=pk)
        post.category = Category.objects.get(pk=request.data["category_id"])
        post.title = request.data["title"]
        # format, imgstr = request.data["image_url"].split(';base64,')
        # ext = format.split('/')[-1]
        # data = ContentFile(base64.b64decode(imgstr), name=f'{request.data["gameId"]}-{uuid.uuid4()}.{ext}')
        # post.image_url = data
        post.content = request.data["content"]

        post.save()
        post.tags.set([tag["id"] for tag in request.data["tags"]])

        # 204 status code means everything worked but the
        # server is not sending back any data in the response
        return Response({}, status=status.HTTP_204_NO_CONTENT)

    def destroy(self, request, pk=None):
        """Handle DELETE requests for a single post

        Returns:
            Response -- 200, 404, or 500 status code
        """
        try:
            post = Post.objects.get(pk=pk)
            post.delete()

            return Response({}, status=status.HTTP_204_NO_CONTENT)

        except Post.DoesNotExist as ex:
            return Response({'message': ex.args[0]}, status=status.HTTP_404_NOT_FOUND)

        except Exception as ex:
            return Response({'message': ex.args[0]}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def list(self, request):
        """Handle GET requests to posts resource

        Returns:
            Response -- JSON serialized list of posts
        """
        # Get all post records from the database
        posts = Post.objects.all()

        # Support filtering posts by type
        #    http://localhost:8000/posts?type=1
        #
        # That URL will retrieve all tabletop posts

        # post_user = self.request.query_params.get('user', None)
        # if post_user is not None:
        #     posts = posts.filter(post_type__id=post_type)

        serializer = PostSerializer(
            posts, many=True, context={'request': request})
        return Response(serializer.data)

    @action(methods=['get'], detail=False)
    def myposts(self, request):
        posts = Post.objects.all()
        user = User.objects.get(username=request.auth.user)
        if user is not None:
            posts = posts.filter(user__id=user.id)
        try:
            serializer = PostSerializer(posts, many=True, context={'request': request})
            return Response(serializer.data)
        except Exception as ex:
            return({'message': ex.args[0]})

    @action(methods=['put'], detail=True)
    def approve(self, request, pk=None):
        post = Post.objects.get(pk=pk)
        post.approved = request.data['approved']
        try:
            post.save()
            serializer = PostSerializer(post, many=False, context={'request': request})
            return Response(serializer.data)
        except Exception as ex:
            return Response({'message': ex.args[0]})
        
