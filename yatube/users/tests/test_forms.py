from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


class UsersCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create(username='userposts')

    def setUp(self):
        self.guest_client = Client()

    def test_create_new_user(self):
        """Проверка добавления нового пользователя
           в базу данных.
        """
        users_count = User.objects.count()
        form_data = {
            'username': 'testuser',
            'password1': '123Testtest',
            'password2': '123Testtest',
        }
        response = self.guest_client.post(
            reverse('users:signup'),
            data=form_data,
            follow=True
        )
        self.assertEqual(User.objects.count(), users_count + 1)
        self.assertRedirects(response, reverse('posts:index'))
