"""View module for handling requests about comments"""
from django.core.exceptions import ValidationError
from django.http import HttpResponseServerError
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import serializers
from rest_framework import status
from django.contrib.auth.models import User  # pylint:disable=imported-auth-user
from rareapi.models import Comment, Category, Post
from rest_framework.decorators import action


# class UserSerializer(serializers.ModelSerializer):
#     """JSON serializer for comment host's related Django user"""
#     class Meta:
#         model = User
#         fields = ('first_name', 'last_name', 'email')

class CommentSerializer(serializers.ModelSerializer):
    """JSON serializer for comments

    Arguments:
        serializer type
    """
    # user = UserSerializer(many=False)
    
    class Meta:
        model = Comment
        fields = ('id', 'content', 'created_on', 'post' )
        depth = 1


class CommentView(ViewSet):
    """Level up comments"""

    def create(self, request):
        """Handle COMMENT operations

        Returns:
            Response -- JSON serialized comment instance
        """

        # Uses the token passed in the `Authorization` header
        user = User.objects.get(username=request.auth.user)

        # Create a new Python instance of the Comment class
        # and set its properties from what was sent in the
        # body of the request from the client.
        comment = Comment()

        comment.user = user
        comment.post = Post.objects.get(pk=request.data['post_id'])
        comment.content = request.data["content"]
        comment.created_on = request.data["created_on"]

        # Use the Django ORM to get the record from the database
        # whose `id` is what the client passed as the
        # `commentTypeId` in the body of the request.

        # ? comment = CommentType.objects.get(pk=request.data["commentTypeId"])
        # ? comment.comment = comment

        # Try to save the new comment to the database, then
        # serialize the comment instance as JSON, and send the
        # JSON as a response to the client request
        try:
            comment.save()
            serializer = CommentSerializer(comment, context={'request': request})
            return Response(serializer.data)

        # If anything went wrong, catch the exception and
        # send a response with a 400 status code to tell the
        # client that something was wrong with its request data
        except ValidationError as ex:
            return Response({"reason": ex.message}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        """Handle GET requests for single comment

        Returns:
            Response -- JSON serialized comment instance
        """
        try:
            # `pk` is a parameter to this function, and
            # Django parses it from the URL route parameter
            #   http://localhost:8000/comments/2
            #
            # The `2` at the end of the route becomes `pk`
            comment = Comment.objects.get(pk=pk)
            serializer = CommentSerializer(comment, context={'request': request})
            return Response(serializer.data)
        except Exception as ex:
            return HttpResponseServerError(ex)

    def update(self, request, pk=None):
        """Handle PUT requests for a comment

        Returns:
            Response -- Empty body with 204 status code
        """
        # Do mostly the same thing as COMMENT, but instead of
        # creating a new instance of Comment, get the comment record
        # from the database whose primary key is `pk`
        # Via query params, PK becomes whatever ID is passed through the param
        comment = Comment.objects.get(pk=pk)
        comment.content = request.data["content"]

        comment.save()

        # 204 status code means everything worked but the
        # server is not sending back any data in the response
        return Response({}, status=status.HTTP_204_NO_CONTENT)

    def destroy(self, request, pk=None):
        """Handle DELETE requests for a single comment

        Returns:
            Response -- 200, 404, or 500 status code
        """
        try:
            comment = Comment.objects.get(pk=pk)
            comment.delete()

            return Response({}, status=status.HTTP_204_NO_CONTENT)

        except Comment.DoesNotExist as ex:
            return Response({'message': ex.args[0]}, status=status.HTTP_404_NOT_FOUND)

        except Exception as ex:
            return Response({'message': ex.args[0]}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def list(self, request):
        """Handle GET requests to comments resource

        Returns:
            Response -- JSON serialized list of comments
        """
        # Get all comment records from the database
        comments = Comment.objects.all()

        serializer = CommentSerializer(
            comments, many=True, context={'request': request})
        return Response(serializer.data)

