## English vocabulary coverage

English repository coverage and translation pipeline only; not ISL grammar, accuracy or signer evaluation.
Source language: en-IN. Deterministic offline Indic-to-English demo glossary then English lookup/gloss; no model calls.

Sentences: 60; measurement errors: 0; FS: 8/275 (2.9%).

FS tokens / emitted gloss tokens in successfully measured sentences. OOV ranking excludes name_heuristic and explicit tokens.

| Source sentence | English intermediate | Gloss | FS count | Notice |
| --- | --- | --- | ---: | --- |
| I am going to college tomorrow. | I am going to college tomorrow. | TOMORROW I COLLEGE GO | 0 | Unverified grammar (demo rules): legacy_category_order, legacy_function_word_filter. |
| Where is the library on campus? | Where is the library on campus? | LIBRARY CAMPUS WHERE | 0 | Unverified grammar (demo rules): demo_function_word_filter_2, legacy_category_order, legacy_function_word_filter. |
| The classroom is near the main gate. | The classroom is near the main gate. | CLASSROOM NEAR FS:MAIN GATE | 1 | Unverified grammar (demo rules): legacy_function_word_filter. |
| Please help me find the science lab. | Please help me find the science lab. | PLEASE ME LABORATORY HELP FIND | 0 | Unverified grammar (demo rules): legacy_category_order, legacy_function_word_filter. |
| I need a notebook for class. | I need a notebook for class. | I NOTEBOOK CLASS NEED | 0 | Unverified grammar (demo rules): demo_function_word_filter_2, legacy_category_order, legacy_function_word_filter. |
| Our exam starts at nine tomorrow. | Our exam starts at nine tomorrow. | TOMORROW OUR EXAM NINE START | 0 | Unverified grammar (demo rules): demo_function_word_filter_2, legacy_category_order. |
| The teacher is waiting in the office. | The teacher is waiting in the office. | TEACHER OFFICE WAIT | 0 | Unverified grammar (demo rules): demo_function_word_filter_2, legacy_category_order, legacy_function_word_filter. |
| I left my bag in the lecture hall. | I left my bag in the lecture hall. | I MY BAG LECTURE_HALL LEAVE | 0 | Unverified grammar (demo rules): demo_function_word_filter_2, legacy_category_order, legacy_function_word_filter. |
| Can we meet after the workshop? | Can we meet after the workshop? | AFTER WE WORKSHOP MEET | 0 | Unverified grammar (demo rules): legacy_category_order, legacy_function_word_filter. |
| The bus to campus is late. | The bus to campus is late. | BUS CAMPUS LATE | 0 | Unverified grammar (demo rules): legacy_function_word_filter. |
| I want to join the sports club. | I want to join the sports club. | I SPORT CLUB WANT JOIN | 0 | Unverified grammar (demo rules): legacy_category_order, legacy_function_word_filter. |
| Please tell me where the hostel is. | Please tell me where the hostel is. | PLEASE ME HOSTEL TELL WHERE | 0 | Unverified grammar (demo rules): legacy_category_order, legacy_function_word_filter. |
| Where is the nearest hospital? | Where is the nearest hospital? | NEAR HOSPITAL WHERE | 0 | Unverified grammar (demo rules): legacy_category_order, legacy_function_word_filter. |
| I need help with this appointment. | I need help with this appointment. | I THIS APPOINTMENT NEED HELP | 0 | Unverified grammar (demo rules): demo_function_word_filter_2, legacy_category_order. |
| My mother has a fever today. | My mother has a fever today. | TODAY MY MOTHER FEVER | 0 | Unverified grammar (demo rules): legacy_category_order, legacy_function_word_filter. |
| Please call a doctor for my father. | Please call a doctor for my father. | PLEASE DOCTOR MY FATHER CALL | 0 | Unverified grammar (demo rules): demo_function_word_filter_2, legacy_category_order, legacy_function_word_filter. |
| The nurse asked me to wait here. | The nurse asked me to wait here. | NURSE ME ASK WAIT | 0 | Unverified grammar (demo rules): demo_function_word_filter_2, legacy_category_order, legacy_function_word_filter. |
| I need water and a place to sit. | I need water and a place to sit. | I WATER FS:PLACE NEED SIT | 1 | Unverified grammar (demo rules): demo_function_word_filter_2, legacy_category_order, legacy_function_word_filter. |
| Where can I collect my medicine? | Where can I collect my medicine? | I MY MEDICINE COLLECT WHERE | 0 | Unverified grammar (demo rules): legacy_category_order, legacy_function_word_filter. |
| My stomach hurts after eating. | My stomach hurts after eating. | AFTER MY STOMACH HURT EAT | 0 | Unverified grammar (demo rules): legacy_category_order. |
| The clinic opens at eight tomorrow. | The clinic opens at eight tomorrow. | TOMORROW CLINIC EIGHT OPEN | 0 | Unverified grammar (demo rules): demo_function_word_filter_2, legacy_category_order, legacy_function_word_filter. |
| Please show me the emergency entrance. | Please show me the emergency entrance. | PLEASE ME EMERGENCY ENTRANCE SHOW | 0 | Unverified grammar (demo rules): legacy_category_order, legacy_function_word_filter. |
| I brought the reports from yesterday. | I brought the reports from yesterday. | YESTERDAY I REPORT BRING | 0 | Unverified grammar (demo rules): demo_function_word_filter_2, legacy_category_order, legacy_function_word_filter. |
| Can my sister stay with me? | Can my sister stay with me? | MY SISTER FS:STAY ME | 1 | Unverified grammar (demo rules): demo_function_word_filter_2, legacy_function_word_filter. |
| I want a ticket to the airport. | I want a ticket to the airport. | I TICKET AIRPORT WANT | 0 | Unverified grammar (demo rules): legacy_category_order, legacy_function_word_filter. |
| Where does this train stop? | Where does this train stop? | THIS TRAIN STOP WHERE | 0 | Unverified grammar (demo rules): legacy_category_order, legacy_function_word_filter. |
| The next bus arrives in ten minutes. | The next bus arrives in ten minutes. | MINUTE NEXT BUS TEN ARRIVE | 0 | Unverified grammar (demo rules): demo_function_word_filter_2, legacy_category_order, legacy_function_word_filter. |
| Please help me find my seat. | Please help me find my seat. | PLEASE ME MY SEAT HELP FIND | 0 | Unverified grammar (demo rules): legacy_category_order. |
| I left my suitcase at the station. | I left my suitcase at the station. | I MY SUITCASE STATION LEAVE | 0 | Unverified grammar (demo rules): demo_function_word_filter_2, legacy_category_order, legacy_function_word_filter. |
| We are going home tomorrow. | We are going home tomorrow. | TOMORROW WE HOME GO | 0 | Unverified grammar (demo rules): legacy_category_order, legacy_function_word_filter. |
| Is the hotel near the market? | Is the hotel near the market? | HOTEL NEAR MARKET | 0 | Unverified grammar (demo rules): legacy_function_word_filter. |
| I need directions to the bus stand. | I need directions to the bus stand. | I FS:DIRECTIONS BUS_STAND NEED | 1 | Unverified grammar (demo rules): legacy_category_order, legacy_function_word_filter. |
| Can you tell me when to get off? | Can you tell me when to get off? | YOU ME FS:GET FS:OFF TELL WHEN | 2 | Unverified grammar (demo rules): legacy_category_order, legacy_function_word_filter. |
| My flight is delayed by two hours. | My flight is delayed by two hours. | HOUR MY FLIGHT LATE TWO | 0 | Unverified grammar (demo rules): demo_function_word_filter_2, legacy_category_order, legacy_function_word_filter. |
| There is a taxi outside the gate. | There is a taxi outside the gate. | TAXI FS:OUTSIDE GATE | 1 | Unverified grammar (demo rules): demo_function_word_filter_2, legacy_function_word_filter. |
| Please wait here while I buy a ticket. | Please wait here while I buy a ticket. | PLEASE FS:WHILE I TICKET WAIT BUY | 1 | Unverified grammar (demo rules): demo_function_word_filter_2, legacy_category_order, legacy_function_word_filter. |
| Yesterday I went to the market and bought vegetables. | Yesterday I went to the market and bought vegetables. | YESTERDAY I MARKET VEGETABLE GO BUY | 0 | Unverified grammar (demo rules): demo_function_word_filter_2, legacy_category_order, legacy_function_word_filter. |
| How much does this shirt cost? | How much does this shirt cost? | MUCH THIS SHIRT COST HOW | 0 | Unverified grammar (demo rules): legacy_category_order, legacy_function_word_filter. |
| I want to buy rice and milk. | I want to buy rice and milk. | I RICE MILK WANT BUY | 0 | Unverified grammar (demo rules): demo_function_word_filter_2, legacy_category_order, legacy_function_word_filter. |
| Do you have these shoes in blue? | Do you have these shoes in blue? | YOU THESE SHOE BLUE | 0 | Unverified grammar (demo rules): demo_function_word_filter_2, legacy_function_word_filter. |
| Please give me a smaller bag. | Please give me a smaller bag. | PLEASE ME SMALL BAG GIVE | 0 | Unverified grammar (demo rules): legacy_category_order, legacy_function_word_filter. |
| I paid for the groceries with cash. | I paid for the groceries with cash. | I GROCERY CASH PAY | 0 | Unverified grammar (demo rules): demo_function_word_filter_2, legacy_category_order, legacy_function_word_filter. |
| Where is the nearest fruit shop? | Where is the nearest fruit shop? | NEAR FRUIT SHOP WHERE | 0 | Unverified grammar (demo rules): legacy_category_order, legacy_function_word_filter. |
| This bottle is for my sister. | This bottle is for my sister. | THIS BOTTLE MY SISTER | 0 | Unverified grammar (demo rules): demo_function_word_filter_2, legacy_function_word_filter. |
| Can I exchange that jacket tomorrow? | Can I exchange that jacket tomorrow? | TOMORROW I THAT JACKET EXCHANGE | 0 | Unverified grammar (demo rules): legacy_category_order, legacy_function_word_filter. |
| The shop is closed on Sunday. | The shop is closed on Sunday. | SUNDAY SHOP CLOSED | 0 | Unverified grammar (demo rules): demo_function_word_filter_2, legacy_category_order, legacy_function_word_filter. |
| I need bread but not butter. | I need bread but not butter. | I BREAD BUTTER NEED NOT | 0 | Unverified grammar (demo rules): demo_function_word_filter_2, legacy_category_order. |
| Please keep those apples in this basket. | Please keep those apples in this basket. | PLEASE THOSE APPLE THIS BASKET KEEP | 0 | Unverified grammar (demo rules): demo_function_word_filter_2, legacy_category_order. |
| My father and mother are at home. | My father and mother are at home. | MY FATHER MOTHER HOME | 0 | Unverified grammar (demo rules): demo_function_word_filter_2, legacy_function_word_filter. |
| I am visiting my grandmother tomorrow. | I am visiting my grandmother tomorrow. | TOMORROW I MY GRANDMOTHER VISIT | 0 | Unverified grammar (demo rules): legacy_category_order, legacy_function_word_filter. |
| My brother goes to college by bus. | My brother goes to college by bus. | MY BROTHER COLLEGE BUS GO | 0 | Unverified grammar (demo rules): demo_function_word_filter_2, legacy_category_order, legacy_function_word_filter. |
| Please help my sister with her homework. | Please help my sister with her homework. | PLEASE MY SISTER HER HOMEWORK HELP | 0 | Unverified grammar (demo rules): demo_function_word_filter_2, legacy_category_order. |
| We eat dinner together in the evening. | We eat dinner together in the evening. | EVENING WE DINNER TOGETHER EAT | 0 | Unverified grammar (demo rules): demo_function_word_filter_2, legacy_category_order, legacy_function_word_filter. |
| I bought a gift for my cousin. | I bought a gift for my cousin. | I GIFT MY COUSIN BUY | 0 | Unverified grammar (demo rules): demo_function_word_filter_2, legacy_category_order, legacy_function_word_filter. |
| The children are playing near the house. | The children are playing near the house. | CHILD NEAR HOUSE PLAY | 0 | Unverified grammar (demo rules): legacy_category_order, legacy_function_word_filter. |
| My aunt is coming from the village. | My aunt is coming from the village. | MY AUNT VILLAGE COME | 0 | Unverified grammar (demo rules): demo_function_word_filter_2, legacy_category_order, legacy_function_word_filter. |
| Can you call me after lunch? | Can you call me after lunch? | AFTER YOU ME LUNCH CALL | 0 | Unverified grammar (demo rules): legacy_category_order, legacy_function_word_filter. |
| I want to see my family this weekend. | I want to see my family this weekend. | WEEKEND I MY FAMILY THIS WANT SEE | 0 | Unverified grammar (demo rules): legacy_category_order, legacy_function_word_filter. |
| We will go home if it rains. | We will go home if it rains. | WE HOME IT GO RAIN | 0 | Unverified grammar (demo rules): demo_function_word_filter_2, legacy_category_order, legacy_function_word_filter. |
| My grandfather likes tea or coffee in the morning. | My grandfather likes tea or coffee in the morning. | MORNING MY GRANDFATHER TEA COFFEE LIKE | 0 | Unverified grammar (demo rules): demo_function_word_filter_2, legacy_category_order, legacy_function_word_filter. |

### Out-of-vocabulary words

| Word | Frequency | Lemma tried |
| --- | ---: | --- |
| directions | 1 | direction |
| get | 1 | get |
| main | 1 | main |
| off | 1 | off |
| outside | 1 | outside |
| place | 1 | place |
| stay | 1 | stay |
| while | 1 | while |
