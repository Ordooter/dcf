# -*- coding:utf-8 -*-

from decimal import Decimal

from django.db import models
from django.conf import settings
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.contrib.sites.models import Site
from django.template.defaultfilters import slugify
from django.core.urlresolvers import reverse
from sorl.thumbnail import ImageField
from unidecode import unidecode


class CurrencyField(models.DecimalField):
    __metaclass__ = models.SubfieldBase

    def to_python(self, value):
        try:
            return super(CurrencyField, self).to_python(value).quantize(Decimal("0.01"))
        except AttributeError:
            return None


class Section(models.Model):

    title = models.CharField(u'название', max_length=100)

    def __unicode__(self):
        return self.title

    def count(self):
        return Item.objects.filter(is_active=True).filter(group__section=self).count()


class Group(models.Model):

    slug = models.SlugField(blank=True, null=True)
    title = models.CharField(u'название', max_length=100)
    section = models.ForeignKey('Section')

    def __unicode__(self):
        return u'%s - %s' % (self.section.title, self.title)

    def count(self):
        return self.item_set.filter(is_active=True).count()

    class Meta:
        ordering = ['section__title', 'title', ]

    def get_title(self):
        return u'%s' % self.title

    def save(self, *args, **kwargs):
        if self.slug is None:
            self.slug = slugify(unidecode(self.title))
            print self.slug
        super(Group, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('group', kwargs={'pk': self.pk, 'slug': self.slug})


class Profile(models.Model):

    user = models.OneToOneField(settings.AUTH_USER_MODEL)
    phone = models.CharField(u'phone', max_length=30, null=True, blank=True)
    receive_news = models.BooleanField(u'receive news', default=True, db_index=True)

    def __unicode__(self):
        return self.user.email

    def allow_add_item(self):

        # TODO add check for blocking

        if self.user.item_set.count() > settings.DCF['ITEM_PER_USER_LIMIT']:
            return False
        else:
            return True

    def count(self):
        return self.user.item_set.count()


class Item(models.Model):

    slug = models.SlugField(blank=True, null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    group = models.ForeignKey(Group, verbose_name="group")

    title = models.CharField('title', max_length=100)
    description = models.TextField('description')
    price = CurrencyField('price', max_digits=10, decimal_places=2)
    phone = models.CharField('phone', max_length=30)

    is_active = models.BooleanField('display', default=True, db_index=True)

    updated = models.DateTimeField('updated', auto_now=True, db_index=True)
    posted = models.DateTimeField('posted', auto_now_add=True)

    def __unicode__(self):
        return self.title

    class Meta:
        ordering = ('-updated', )

    def get_absolute_url(self):
        return reverse('item', kwargs={'pk': self.pk, 'slug': self.slug})

    def get_title(self):
        return u'%s' % self.title

    def get_description(self):

        return u'%s' % self.description[:155]

    def get_keywords(self):

        # TODO need more optimal keywords selection
        return ",".join(set(self.description.split()))

    def get_related(self):

        # TODO Need more complicated related select
        return Item.objects.exclude(pk=self.pk)[:settings.DCF['RELATED_LIMIT']]

    def save(self, *args, **kwargs):
        if self.slug is None:
            self.slug = slugify(unidecode(self.title))
        super(Item, self).save(*args, **kwargs)


class Image(models.Model):

    item = models.ForeignKey(Item)
    file = ImageField(u'image', upload_to='images')


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)