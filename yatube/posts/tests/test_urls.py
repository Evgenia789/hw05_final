from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from posts.models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
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
        cls.templates_url_names = {
            '/': 'posts/index.html',
            f'/group/{PostURLTests.group.slug}/': 'posts/group_list.html',
            f'/profile/{PostURLTests.author.username}/': 'posts/profile.html',
            f'/posts/{PostURLTests.post.id}/': 'posts/post_detail.html',
            f'/posts/{PostURLTests.post.id}/edit/': 'posts/create_post.html',
            '/create/': 'posts/create_post.html'
        }
        cls.templates_url_create_and_edit = [
            f'/posts/{PostURLTests.post.id}/edit/',
            '/create/'
        ]

    def setUp(self):
        self.user = User.objects.create_user(username='HasNoName')
        self.authorized_client_not_author = Client()
        self.authorized_client_not_author.force_login(self.user)
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)

    def test_url_exists_at_desired_location(self):
        """Страницы доступные любому пользователю."""
        for adress in PostURLTests.templates_url_names.keys():
            if adress not in PostURLTests.templates_url_create_and_edit:
                with self.subTest(adress=adress):
                    response = self.client.get(adress)
                    self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_posts_exists_at_desired_location(self):
        """Страницы доступные авторизованному
           пользователю (не автору поста).
        """
        for adress in PostURLTests.templates_url_names.keys():
            if adress != PostURLTests.templates_url_create_and_edit[0]:
                with self.subTest(adress=adress):
                    response = self.authorized_client_not_author.get(adress)
                    self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_edit_exists_at_desired_location_authorized(self):
        """Страница /posts/<post_id>/edit/ доступна
           авторизованному пользователю (автору поста).
        """
        response = self.authorized_client.get(
            PostURLTests.templates_url_create_and_edit[0]
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_posts_list_url_redirect_anonymous(self):
        """Страницы /posts/<post_id>/edit/ и /create/
           перенаправляют анонимного пользователя.
        """
        for adress in PostURLTests.templates_url_names.keys():
            if adress in PostURLTests.templates_url_create_and_edit:
                with self.subTest(adress=adress):
                    response = self.client.get(adress)
                    self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_post_edit_url_redirect_location_authorized(self):
        """Страница по адресу /posts/<post_id>/edit/ перенаправит
           авторизованного пользователя (не автора поста)"""
        response = self.authorized_client_not_author.get(
            PostURLTests.templates_url_create_and_edit[0]
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_posts_edit_url_redirect_anonymous_on_admin_login(self):
        """Страница по адресу /posts/<post_id>/edit/ перенаправит
        анонимного пользователя на страницу логина.
        """
        response = self.client.get(
            PostURLTests.templates_url_create_and_edit[0],
            follow=True
        )
        self.assertRedirects(
            response, f'/auth/login/?next=/posts/{PostURLTests.post.id}/edit/'
        )

    def test_posts_create_url_redirect_anonymous_on_admin_login(self):
        """Страница по адресу /create/ перенаправит анонимного
        пользователя на страницу логина.
        """
        response = self.client.get(
            PostURLTests.templates_url_create_and_edit[1],
            follow=True
        )
        self.assertRedirects(
            response, ('/auth/login/?next=/create/'))

    def test_post_edit_url_redirect_authorized_client_not_author(self):
        """Страница по адресу /posts/<post_id>/edit/
        перенаправит авторизованного пользователя
        (не автора поста) на страницу поста.
        """
        response = self.authorized_client_not_author.get(
            PostURLTests.templates_url_create_and_edit[0],
            follow=True
        )
        self.assertRedirects(
            response, f'/posts/{PostURLTests.post.id}/'
        )

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for adress, template in PostURLTests.templates_url_names.items():
            with self.subTest(adress=adress):
                response = self.authorized_client.get(adress, follow=True)
                self.assertTemplateUsed(response, template)

    def test_404(self):
        """Запрос к несуществующей странице вернёт ошибку 404"""
        response = self.client.get('/posts/cat_dog/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
