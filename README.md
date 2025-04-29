# Mtihani API

## Commands

```bash
source .venv/bin/activate
pip freeze > requirements.txt
django-admin startapp appName
source .venv/bin/activate && cd mtihaniapi && python3 manage.py runserver
python manage.py makemigrations && python manage.py migrate # for all apps
python manage.py makemigrations accounts && python manage.py migrate accounts # for a specific app
python manage.py createsuperuser
python3 mtihanigen/mtihani_chat.py
```

## SetUp Process
- Create superusers
- Create system roles: admin, teacher, user
- Upload cbc JSONs
- Register teachers & classes & students (teacherOne: grade 7 & 8, teacherTwo: grade 9)


```bash
(mtihani-api-py3.11) mtihani-api-py3.11melaniefayne@Melanies-MacBook-Pro mtihani_api % python3 mtihanigen/mtihani_chat.py
🎯 Grade 9 -> Strand: Mixtures, Elements and Compounds -> Sub-Strand: Water Hardness

Device set to use cpu
✍️ Generating exam questions...


✅ Exam Questions Generated:

What is a good name for the teacher? for his/her teacher? to know if this is correct?? to see??doar?highschool for a mid-term exam?? ??)??)-?)??bestwestern.best)?of-fundus-gradebcft -and-and-fiction.fiction-fiction.s@america.fmx-ano-the-y,no-the-y,no-go-and-don-sasheinast.the first-and-nifty,h-thy &ld andsa school will graduate first-school grade --ands_its-yearyear-old? ida &his-
(mtihani-api-py3.11) mtihani-api-py3.11melaniefayne@Melanies-MacBook-Pro mtihani_api % python3 mtihanigen/mtihani_chat.py
🎯 Grade 7 -> Strand: Mixtures, Elements and Compounds -> Sub-Strand: Acids, Bases and Indicators

Device set to use cpu
✍️ Generating exam questions...


✅ Exam Questions Generated:

Who did you teach integrase from? me me.?u.k??u.do?u.th?ug.?ug.ll?ug.?ug.gl?ug..h?ug.diasf?ug?? wr?ugb.?.ro?)?r?.-?-beas alum-goableamount.factop.crbbcbcbcbbcabcfbctb.lyanci?ug.helg.-ado-norfabebda's?ug.as.acstart.pbd?ug.d.he"da?ug..-than-now-ref.we're a student in middle 20th?'k'?they're for? . What the top.?s sas ''don's??''daa?'s?you'd??y's and they're a student should study?''.'s? where?'ss'd name?the title is? a teacher should be in-noones. the grade 7 grade first year is an engineering college n's-a grade 7?-no-frightensowhat?-thgrade?"-whose grades of sciencefor _you's grade 7 from this grade-gourase s sa u.-in x?-bc?-cf'nred is the first grade--/st-that's grade 7grade-say-grade-star-loas grade-gradean" .d)'ly-'')-super--thhightechthough&th-grade")sthe-saysthstillgrade")medaforfthan@bradgradeforssecond-gradedlumviewthhighvaluefacttest
```

