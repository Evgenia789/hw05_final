import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Comment, Follow, Group, Post

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
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
            group=cls.group,
            image=cls.uploaded
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list',
                kwargs={'slug': f'{PostPagesTests.group.slug}'}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile',
                kwargs={'username': f'{PostPagesTests.author.username}'}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail',
                kwargs={'post_id': f'{PostPagesTests.post.id}'}
            ): 'posts/post_detail.html',
            reverse(
                'posts:post_edit',
                kwargs={'post_id': f'{PostPagesTests.post.id}'}
            ): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html'
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def correct_context(self, response, **kwarg):
        if len(kwarg) >= 2:
            object_count = response.context.get('posts_author')
            self.assertEqual(
                response.context.get('post').author,
                PostPagesTests.author
            )
            self.assertEqual(
                response.context.get('post').group,
                PostPagesTests.group
            )
            self.assertEqual(
                response.context.get('post').text,
                PostPagesTests.post.text
            )
            self.assertEqual(
                response.context.get('post').image,
                PostPagesTests.post.image
            )
            self.assertEqual(1, object_count)
        else:
            first_object = response.context.get('page_obj').object_list[0]
            post_text_0 = first_object.text
            post_author_0 = first_object.author
            post_group_0 = first_object.group
            post_image_0 = first_object.image
            self.assertEqual(post_text_0, PostPagesTests.post.text)
            self.assertEqual(post_author_0, PostPagesTests.author)
            self.assertEqual(post_group_0, PostPagesTests.group)
            self.assertEqual(post_image_0, PostPagesTests.post.image)

        if kwarg is not None:
            for k, v in kwarg.items():
                object = response.context.get(f'{k}')
                self.assertEqual(v, object)

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом
           (список постов).
        """
        response = self.authorized_client.get(reverse('posts:index'))
        self.correct_context(response)

    def test_group_posts_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом
           (список постов отфильтрованных по группе).
        """
        response = self.authorized_client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': f'{PostPagesTests.group.slug}'}
            )
        )
        self.correct_context(response, group=PostPagesTests.group)

    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом
           (список постов отфильтрованных по пользователю).
        """
        response = self.authorized_client.get(
            reverse(
                'posts:profile',
                kwargs={'username': f'{PostPagesTests.author.username}'}
            )
        )
        self.correct_context(response, author=PostPagesTests.author)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом
           (один пост, отфильтрованный по id).
        """
        response = self.authorized_client.get(
            reverse(
                'posts:post_detail',
                kwargs={'post_id': f'{PostPagesTests.post.id}'}
            )
        )
        self.correct_context(
            response,
            author=PostPagesTests.author,
            post_id=PostPagesTests.post.id
        )

    def test_edit_post_detail_page_show_correct_context(self):
        """Шаблон create_post сформирован с правильным контекстом
           (форма редактирования поста отфильтрованного по id).
        """
        response = self.authorized_client.get(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': f'{PostPagesTests.post.id}'}
            )
        )
        object_post = response.context.get('post')
        object_is_edit = response.context.get('is_edit')
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

        self.assertEqual(PostPagesTests.post.id, object_post.id)
        self.assertEqual(False, object_is_edit)

    def test_create_post_detail_page_show_correct_context(self):
        """Шаблон create_post сформирован с правильным контекстом
           (форма создания поста).
        """
        response = self.authorized_client.get(reverse('posts:post_create'))
        object_is_edit = response.context.get('is_edit')
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

        self.assertEqual(True, object_is_edit)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create(username='userposts')
        cls.group = Group.objects.create(
            title='Тестовое название',
            slug='test-slug',
            description='Тестовое описание группы'
        )
        cls.group_2 = Group.objects.create(
            title='Тестовое название_2',
            slug='test-slug-2',
            description='Тестовое описание группы_2'
        )
        for _ in range(13):
            cls.post = Post.objects.create(
                text='Тестовый текст',
                author=cls.author,
                group=cls.group
            )
        cls.templates_url_names = [
            reverse('posts:index'),
            reverse(
                'posts:group_list',
                kwargs={'slug': f'{cls.group.slug}'}
            ),
            reverse(
                'posts:profile',
                kwargs={'username': f'{cls.author.username}'}
            )
        ]

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)

    def test_first_page_contains_ten_records(self):
        for adress in PaginatorViewsTest.templates_url_names:
            response = self.authorized_client.get(adress)
            self.assertEqual(
                len(response.context.get('page_obj').object_list),
                settings.PAGE_COUNT
            )

    def test_second_page_contains_three_records(self):
        posts_count = Post.objects.count() % 10
        for adress in PaginatorViewsTest.templates_url_names:
            response = self.authorized_client.get(adress + '?page=2')
            self.assertEqual(
                len(response.context.get('page_obj').object_list),
                posts_count
            )

    def test_post_view(self):
        """Шаблоны index, group_list, profile отображают созданный пост с
           указанной группой.
        """
        for adress in PaginatorViewsTest.templates_url_names:
            response = self.authorized_client.get(adress)
            first_object = response.context.get('page_obj').object_list[0]
            post_group_0 = first_object.group
            self.assertEqual(post_group_0, PaginatorViewsTest.group)

    def test_post_view_need(self):
        """Созданный пост не отображается на странице группы,
           которой не предназначен.
        """
        response = self.authorized_client.get(self.templates_url_names[2])
        first_object = response.context.get('page_obj').object_list[0]
        post_group_0 = first_object.group
        self.assertNotEqual(post_group_0, PaginatorViewsTest.group_2)


class CommentViewsTest(TestCase):
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
        cls.comment = Comment.objects.create(
            author=cls.author,
            text='Тестовый комментарий',
            post=cls.post
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)

    def test_comment_view(self):
        """Шаблоны post_detail отображают созданный комментарий на
        странице поста.
        """
        response = self.authorized_client.get(
            reverse(
                'posts:post_detail',
                kwargs={'post_id': f'{CommentViewsTest.post.id}'}
            )
        )
        first_object = response.context.get('comments')[0]
        comment_post_0 = first_object
        self.assertEqual(comment_post_0, CommentViewsTest.comment)


class CacheViewsTest(TestCase):
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

    def test_cach(self):
        """Проверяет работу кеша.
        """
        response = self.authorized_client.get(
            reverse('posts:index')
        )
        content_post = response.content
        Post.objects.filter(id=self.post.id).delete()
        response = self.authorized_client.get(
            reverse('posts:index')
        )
        self.assertEqual(content_post, response.content)
        cache.clear()
        response = self.authorized_client.get(
            reverse('posts:index')
        )
        self.assertNotEqual(content_post, response.content)


class FollowViewsTest(TestCase):
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

    def test_follower_view(self):
        """Новая запись пользователя появляется в ленте
           тех, кто на него подписан.
        """
        Follow.objects.create(user=self.user_1, author=self.author)
        new_post_author = Post.objects.create(
            text='Тестовый текст новый',
            author=self.author,
            group=self.group
        )
        response = self.authorized_client_not_author_1.get(
            reverse('posts:follow_index')
        )
        first_object = response.context.get('page_obj').object_list[0]
        self.assertEqual(first_object, new_post_author)

    def test_not_follower_view(self):
        """Новая запись пользователя не появляется в ленте
           тех, кто на него не подписан.
        """
        Follow.objects.create(user=self.user_2, author=self.user_1)
        Post.objects.create(
            text='Тестовый текст новый',
            author=self.user_1,
            group=self.group
        )
        new_post_author = Post.objects.create(
            text='Тестовый текст самый новый',
            author=self.author,
            group=self.group
        )
        response = self.authorized_client_not_author_2.get(
            reverse('posts:follow_index')
        )
        first_object = response.context.get('page_obj').object_list[0]
        self.assertNotEqual(first_object, new_post_author)
