from django.test import TestCase

# Create your tests here.
import datetime
from django.utils import timezone
from .models import Question
from django.urls import reverse

def create_question(question_text, days):
    """
    Create a question with the given `question_text` and published the
    given number of `days` offset to now (negative for questions published
    in the past, positive for questions that have yet to be published).
    """
    time = timezone.now() + datetime.timedelta(days=days)
    return Question.objects.create(question_text=question_text, pub_date=time)


class QuestionModelTests(TestCase):

    def test_was_published_recently_with_future_question(self):
        """
        was_published_recently() returns False for questions whose pub_date
        is in the future.
        """
        time = timezone.now() + datetime.timedelta(days=30)
        future_question = Question(pub_date=time)
        self.assertIs(future_question.was_published_recently(), False)

    def test_was_published_recently_with_old_question(self):
        """
        was_published_recently() returns False for questions whose pub_date
        is older than 1 day.
        """
        time = timezone.now() - datetime.timedelta(days=1, seconds=1)
        old_question = Question(pub_date=time)
        self.assertIs(old_question.was_published_recently(), False)

    def test_was_published_recently_with_recent_question(self):
        """
        was_published_recently() returns True for questions whose pub_date
        is within the last day.
        """
        time = timezone.now() - datetime.timedelta(hours=23, minutes=59, seconds=59)
        recent_question = Question(pub_date=time)
        self.assertIs(recent_question.was_published_recently(), True)

    def test_future_question_is_not_recent(self):
        future_question = create_question(question_text="Future question.", days=30)
        self.assertIs(future_question.was_published_recently(), False)
        response = self.client.get(reverse('polls:index'))
        self.assertNotContains(response, future_question.question_text)
        self.assertQuerysetEqual(response.context['latest_question_list'], [])

class QuestionIndexViewTests(TestCase):
    def test_empty_index(self):
        response = self.client.get(reverse('polls:index'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(response.context['latest_question_list'], [])

    def test_no_questions(self):
        """
        If no questions exist, an appropriate message is displayed.
        """
        response = self.client.get(reverse('polls:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No polls are available.")
        self.assertQuerysetEqual(response.context['latest_question_list'], [])

    def test_past_question(self):
        """
        Questions with a pub_date in the past are displayed on the
        index page.
        """
        question = create_question(question_text="Past question.", days=-30)
        response = self.client.get(reverse('polls:index'))
        self.assertQuerysetEqual(
            response.context['latest_question_list'],
            [question],
        )

    def test_future_question(self):
        """
        Questions with a pub_date in the future aren't displayed on
        the index page.
        """
        create_question(question_text="Future question.", days=30)
        response = self.client.get(reverse('polls:index'))
        self.assertContains(response, "No polls are available.")
        self.assertQuerysetEqual(response.context['latest_question_list'], [])

    def test_future_question_and_past_question(self):
        """
        Even if both past and future questions exist, only past questions
        are displayed.
        """
        question = create_question(question_text="Past question.", days=-30)
        create_question(question_text="Future question.", days=30)
        response = self.client.get(reverse('polls:index'))
        self.assertQuerysetEqual(
            response.context['latest_question_list'],
            [question],
        )

    def test_two_past_questions(self):
        """
        The questions index page may display multiple questions.
        """
        question1 = create_question(question_text="Past question 1.", days=-30)
        question2 = create_question(question_text="Past question 2.", days=-5)
        response = self.client.get(reverse('polls:index'))
        self.assertQuerysetEqual(
            response.context['latest_question_list'],
            [question2, question1],
        )

class QuestionDetailViewTests(TestCase):
    def test_future_question(self):
        """
        The detail view of a question with a pub_date in the future
        returns a 404 not found.
        """
        future_question = create_question(question_text='Future question.', days=5)
        url = reverse('polls:detail', args=(future_question.id,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_past_question(self):
        """
        The detail view of a question with a pub_date in the past
        displays the question's text.
        """
        past_question = create_question(question_text='Past Question.', days=-5)
        url = reverse('polls:detail', args=(past_question.id,))
        response = self.client.get(url)
        self.assertContains(response, past_question.question_text)


class QuestionVoteTests(TestCase):
    def test_vote_increments_selected_choice(self):
        question = create_question(question_text="Past question.", days=-5)
        selected_choice = question.choice_set.create(choice_text="Choice 1")
        other_choice = question.choice_set.create(choice_text="Choice 2")
        url = reverse('polls:vote', args=(question.id,))
        response = self.client.post(url, {'choice': selected_choice.id})
        self.assertRedirects(response, reverse('polls:results', args=(question.id,)))
        selected_choice.refresh_from_db()
        other_choice.refresh_from_db()
        self.assertEqual(selected_choice.votes, 1)
        self.assertEqual(other_choice.votes, 0)

    def test_vote_with_missing_choice_does_not_increment(self):
        question = create_question(question_text="Past question.", days=-5)
        choice1 = question.choice_set.create(choice_text="Choice 1")
        choice2 = question.choice_set.create(choice_text="Choice 2")
        url = reverse('polls:vote', args=(question.id,))
        response = self.client.post(url, {})
        self.assertContains(response, "You didn&#x27;t select a choice.")
        choice1.refresh_from_db()
        choice2.refresh_from_db()
        self.assertEqual(choice1.votes, 0)
        self.assertEqual(choice2.votes, 0)

    def test_vote_with_nonexistent_choice_does_not_increment(self):
        question = create_question(question_text="Past question.", days=-5)
        choice1 = question.choice_set.create(choice_text="Choice 1")
        choice2 = question.choice_set.create(choice_text="Choice 2")
        url = reverse('polls:vote', args=(question.id,))
        response = self.client.post(url, {'choice': 9999})
        self.assertContains(response, "You didn&#x27;t select a choice.")
        choice1.refresh_from_db()
        choice2.refresh_from_db()
        self.assertEqual(choice1.votes, 0)
        self.assertEqual(choice2.votes, 0)

    def test_vote_with_other_questions_choice_does_not_increment(self):
        question = create_question(question_text="Past question 1.", days=-5)
        other_question = create_question(question_text="Past question 2.", days=-5)
        choice = question.choice_set.create(choice_text="Choice 1")
        other_choice = other_question.choice_set.create(choice_text="Choice 2")
        url = reverse('polls:vote', args=(question.id,))
        response = self.client.post(url, {'choice': other_choice.id})
        self.assertContains(response, "You didn&#x27;t select a choice.")
        choice.refresh_from_db()
        other_choice.refresh_from_db()
        self.assertEqual(choice.votes, 0)
        self.assertEqual(other_choice.votes, 0)
