import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.models import Comment, Follow, Group, Post

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create(username='userposts')
        cls.group = Group.objects.create(
            title='Тестовое название',
            slug='test-slug',
            description='Тестовое описнаие группы'
        )
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.author,
            group=cls.group
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)

    def test_create_new_post(self):
        """Проверка добавления нового поста
           в базу данных.
        """
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый текст_2',
            'group': PostsCreateFormTests.group.id,
            'image': PostsCreateFormTests.uploaded
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertRedirects(
            response,
            reverse(
                'posts:profile',
                kwargs={
                    'username': PostsCreateFormTests.author.username
                }
            )
        )
        lastpost = Post.objects.order_by('-id')[0]
        self.assertTrue(
            Post.objects.filter(
                id=lastpost.id,
                text=form_data['text'],
                author=self.author,
                group=self.group,
                image='posts/small.gif'
            ).exists()
        )

    def test_create_edit_post(self):
        """Проверка изменения поста
           в базе данных при редактировании поста.
        """
        posts_count = Post.objects.count()
        group_new = Group.objects.create(
            title='Тестовое название_2',
            slug='test-slug-2',
            description='Тестовое описнаие группы_2'
        )
        form_data = {
            'text': self.post.text,
            'group': group_new.id
        }
        response = self.authorized_client.post(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': PostsCreateFormTests.post.id}
            ),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertRedirects(
            response,
            reverse(
                'posts:post_detail',
                kwargs={'post_id': PostsCreateFormTests.post.id}
            )
        )
        self.assertTrue(
            Post.objects.filter(
                id=self.post.id,
                text=self.post.text,
                author=self.author,
                group=group_new.id
            ).exists()
        )

    def test_cant_create_anonymous(self):
        """Проверка, что незарегистрированный пользователь
           не сможет создать пост.
        """
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый текст_2',
            'group': PostsCreateFormTests.group.id
        }
        response = self.client.post(
            reverse('posts:post_create'),
            data=form_data
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertRedirects(
            response,
            '/auth/login/?next=/create/'
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_cant_edit_anonymous(self):
        """Проверка, что незарегистрированный пользователь
           не сможет отредактировать пост.
        """
        posts_count = Post.objects.count()
        group_new = Group.objects.create(
            title='Тестовое название_2',
            slug='test-slug-2',
            description='Тестовое описнаие группы_2'
        )
        form_data = {
            'text': self.post.text,
            'group': group_new.id
        }
        response = self.client.post(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': PostsCreateFormTests.post.id}
            ),
            data=form_data
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertRedirects(
            response,
            f'/auth/login/?next=/posts/{PostsCreateFormTests.post.id}/edit/'
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertTrue(
            Post.objects.filter(
                id=self.post.id,
                text=self.post.text,
                author=self.author,
                group=self.group
            ).exists()
        )


class CommentCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create(username='userposts')
        cls.group = Group.objects.create(
            title='Тестовое название',
            slug='test-slug',
            description='Тестовое описнаие группы'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.author,
            group=cls.group
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)

    def test_create_new_comment(self):
        """Проверка добавления нового комментария
           в базу данных авторизованным пользователем.
        """
        comments_count = Comment.objects.count()
        form_data = {
            'text': 'Тестовый комментарий',
        }
        response = self.authorized_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': CommentCreateFormTests.post.id}
            ),
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertRedirects(
            response,
            reverse(
                'posts:post_detail',
                kwargs={
                    'post_id': CommentCreateFormTests.post.id
                }
            )
        )
        lastcomment = Comment.objects.order_by('-id')[0]
        self.assertTrue(
            Comment.objects.filter(
                id=lastcomment.id,
                text=form_data['text'],
            ).exists()
        )

    def test_cant_create_comment_anonymous(self):
        """Проверка, что незарегистрированный пользователь
           не сможет добавить комментарий.
        """
        comments_count = Comment.objects.count()
        form_data = {
            'text': 'Тестовый комментарий',
        }
        response = self.client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': CommentCreateFormTests.post.id}
            ),
            data=form_data
        )
        self.assertEqual(Comment.objects.count(), comments_count)
        self.assertRedirects(
            response,
            f'/auth/login/?next=/posts'
            f'/{CommentCreateFormTests.post.id}/comment'
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)


class FollowCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create(username='userposts')
        cls.group = Group.objects.create(
            title='Тестовое название',
            slug='test-slug',
            description='Тестовое описание группы'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.author,
            group=cls.group
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)
        self.user_1 = User.objects.create_user(username='HasNoName1')
        self.authorized_client_not_author_1 = Client()
        self.authorized_client_not_author_1.force_login(self.user_1)
        self.user_2 = User.objects.create_user(username='HasNoName2')
        self.authorized_client_not_author_2 = Client()
        self.authorized_client_not_author_2.force_login(self.user_2)

    def test_create_follow(self):
        """Проверка, что авторизованный пользователь
           может подписываться на других пользователей
        """
        follow_count = Follow.objects.count()
        form_data = {
            'username': self.author.username
        }
        response = self.authorized_client_not_author_1.post(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.author.username}
            ),
            data=form_data,
            follow=True
        )
        self.assertEqual(Follow.objects.count(), follow_count + 1)
        self.assertRedirects(
            response,
            reverse(
                'posts:profile',
                kwargs={
                    'username': self.author.username
                }
            )
        )
        self.assertTrue(
            Follow.objects.filter(
                author=self.author,
                user=self.user_1
            ).exists()
        )

    def test_create_unfollow(self):
        """Проверка, что авторизованный пользователь
           может отписываться на других пользователей
        """
        follow = Follow.objects.create(user=self.user_1, author=self.author)
        follow_count = Follow.objects.count()
        follow.delete()
        form_data = {
            'username': self.author.username
        }
        response = self.authorized_client_not_author_1.post(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.author.username}
            ),
            data=form_data,
            follow=True
        )
        self.assertEqual(Follow.objects.count(), follow_count - 1)
        self.assertRedirects(
            response,
            reverse(
                'posts:profile',
                kwargs={
                    'username': self.author.username
                }
            )
        )
        self.assertFalse(
            Follow.objects.filter(
                author=self.author,
                user=self.user_1
            ).exists()
        )
