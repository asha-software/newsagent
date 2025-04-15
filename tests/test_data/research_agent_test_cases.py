"""Test cases for research agent tool usage tests"""

DETAIL_MESSAGE = "\nExpected {expected_tools} to be used, but agent used {tools_used}."

"""
NOTE: Currently setting `expected_tools` to list so that later if we want to test for
tool call sequence, we can.
"""
TOOL_USAGE_TEST_CASES = [
    {
        "claim": "12 multiplied by 10 equals 120",
        "expected_tools": ["multiply"],
        "description": "Calculator tool should be used for mathematical claims." + DETAIL_MESSAGE
    },
    {
        "claim": "Albert Einstein developed the theory of relativity",
        "expected_tools": ["query"],
        "description": "Wikipedia tool should be used for historical claims." + DETAIL_MESSAGE
    },
    {
        "claim": "The capital of France is Berlin",
        "expected_tools": ["query"],
        "description": "Wikipedia tool should be used for geographical claims." + DETAIL_MESSAGE
    },
    # Add more test cases here
]

CALCULATOR_TEST_CASES = [
    {
        "claim": "12 multiplied by 10 equals 120",
        "expected_tools": ["calculator"],
        "description": "A basic arithmetic operation appropriate for the calculator tool."
    },
    {
        "claim": "If I save $5 a day for a year, I'll have $1,825.",
        "expected_tools": ["calculator"],
        "description": "A financial projection that involves multiplication."
    },
    {
        "claim": "The average of 5, 8, and 11 is 8.",
        "expected_tools": ["calculator"],
        "description": "An average calculation should be verified by the calculator."
    },
    {
        "claim": "25% of 80 is 20.",
        "expected_tools": ["calculator"],
        "description": "A percentage calculation is best checked using the calculator tool."
    },
    {
        "claim": "The square root of 144 is 12.",
        "expected_tools": ["calculator"],
        "description": "Basic square root calculation."
    },
    {
        "claim": "2 raised to the 10th power is 1024.",
        "expected_tools": ["calculator"],
        "description": "Exponential calculation should use the calculator."
    },
    {
        "claim": "If a video has 2.5 million views and 10% are likes, that’s 250,000 likes.",
        "expected_tools": ["calculator"],
        "description": "Social media-style percentage-based calculation."
    },
    {
        "claim": "If 3 tickets cost $75 total, then each ticket is $25.",
        "expected_tools": ["calculator"],
        "description": "Division to determine unit price."
    },
    {
        "claim": "A 15% tip on a $60 bill is $9.",
        "expected_tools": ["calculator"],
        "description": "Tipping math—simple percentage of a given amount."
    },
    {
        "claim": "A person burning 500 calories per workout, 4 times a week, burns 2000 calories weekly.",
        "expected_tools": ["calculator"],
        "description": "Basic fitness-related multiplication."
    },
    {
        "claim": "If I drive 300 miles on 10 gallons of gas, I get 30 miles per gallon.",
        "expected_tools": ["calculator"],
        "description": "Division-based fuel efficiency calculation."
    },
    {
        "claim": "40% of 250 is 100.",
        "expected_tools": ["calculator"],
        "description": "Percentage calculation for verification."
    },
    {
        "claim": "There are 1,440 minutes in a day.",
        "expected_tools": ["calculator"],
        "description": "Calculated by multiplying 24 hours by 60 minutes."
    },
    {
        "claim": "7 times 8 is 54.",
        "expected_tools": ["calculator"],
        "description": "Incorrect multiplication that the calculator can correct."
    },
    {
        "claim": "If I make $20/hour and work 40 hours, I earn $800 a week.",
        "expected_tools": ["calculator"],
        "description": "Hourly wage calculation through multiplication."
    },
    {
        "claim": "A YouTube channel with 50k subscribers gaining 10% growth monthly would have 55k the next month.",
        "expected_tools": ["calculator"],
        "description": "Social media growth projection using percentage math."
    },
    {
        "claim": "An item originally $120 with a 25% discount now costs $90.",
        "expected_tools": ["calculator"],
        "description": "Discount calculation involving percentage and subtraction."
    },
    {
        "claim": "If a recipe serves 4 and I need it for 6, I should multiply all ingredients by 1.5.",
        "expected_tools": ["calculator"],
        "description": "Ratio and scaling calculation."
    },
    {
        "claim": "If I sleep 7 hours a night, that’s 49 hours a week.",
        "expected_tools": ["calculator"],
        "description": "Multiplication to total weekly hours."
    },
    {
        "claim": "My $1,000 investment growing at 5% annually will be worth $1,050 after one year.",
        "expected_tools": ["calculator"],
        "description": "Simple interest calculation for one-year growth."
    }
]

WEB_SEARCH_TEST_CASES = [
    {
        "claim": "5G towers are causing birds to drop dead from the sky.",
        "expected_tools": ["web_search"],
        "description": "Contemporary technology claims should be verified via web search."
    },
    {
        "claim": "The 2025 Grammy Awards were held in Los Angeles.",
        "expected_tools": ["web_search"],
        "description": "Current events like award shows should be looked up via the web."
    },
    {
        "claim": "OpenAI released a new GPT model this month.",
        "expected_tools": ["web_search"],
        "description": "Recent product launches require web lookup."
    },
    {
        "claim": "Manchester United won their last match.",
        "expected_tools": ["web_search"],
        "description": "Sports results are dynamic and best retrieved via web search."
    },
    {
        "claim": "There is a major traffic disruption on the I-405 freeway today.",
        "expected_tools": ["web_search"],
        "description": "Traffic updates are current and change frequently."
    },
    {
        "claim": "The U.S. government is planning to replace the dollar with a digital currency.",
        "expected_tools": ["web_search"],
        "description": "Current events involving government policy should be verified via web search."
    },
    {
        "claim": "Phones continuously record audio even when turned off.",
        "expected_tools": ["web_search"],
        "description": "Contemporary technology claims should be verified via web search."
    },
    {
        "claim": "Bitcoin's value increased by 5% in the last week.",
        "expected_tools": ["web_search"],
        "description": "Cryptocurrency values change constantly."
    },
    {
        "claim": "Taylor Swift announced new tour dates this week.",
        "expected_tools": ["web_search"],
        "description": "Concert tour announcements are current events."
    },
    {
        "claim": "A 6.0 magnitude earthquake struck California this morning.",
        "expected_tools": ["web_search"],
        "description": "Natural disaster reports require real-time data from the web."
    },
    {
        "claim": "Elon Musk tweeted about AI safety yesterday.",
        "expected_tools": ["web_search"],
        "description": "Social media posts are best verified via web search."
    },
    {
        "claim": "Mark Zuckerberg personally reviews all Facebook messages.",
        "expected_tools": ["web_search"],
        "description": "Sports schedules for current or upcoming events should use the web."
    },
    {
        "claim": "Gas prices in New York are above $4 per gallon this week.",
        "expected_tools": ["web_search"],
        "description": "Gas prices fluctuate and require up-to-date data."
    },
    {
        "claim": "A new law banning single-use plastics just passed in California.",
        "expected_tools": ["web_search"],
        "description": "Recent legislation needs real-time information."
    },
    {
        "claim": "NASA announced a new moon mission this month.",
        "expected_tools": ["web_search"],
        "description": "Recent space program updates are current events."
    },
    {
        "claim": "The unemployment rate in the U.S. increased last quarter.",
        "expected_tools": ["web_search"],
        "description": "Economic indicators are time-sensitive and updated frequently."
    },
    {
        "claim": "A major cybersecurity breach affected several U.S. banks last week.",
        "expected_tools": ["web_search"],
        "description": "Cyber incidents are real-time newsworthy events."
    },
    {
        "claim": "The latest Marvel movie topped the box office this weekend.",
        "expected_tools": ["web_search"],
        "description": "Box office results change weekly and require web lookups."
    },
    {
        "claim": "A new COVID-19 variant was detected this week in Europe.",
        "expected_tools": ["web_search"],
        "description": "Health updates involving disease variants are timely."
    },
    {
        "claim": "The Eiffel Tower is currently being dismantled for renovations.",
        "expected_tools": ["web_search"],
        "description": "International event announcements require current information."
    }
]

WIKIPEDIA_TEST_CASES = [
    {
        "claim": "The moon landing in 1969 was staged by the U.S. government.",
        "expected_tools": ["wikipedia"],
        "description": "A common conspiracy theory; Wikipedia can verify the historical accuracy of the moon landing."
    },
    {
        "claim": "Vaccines cause autism in children.",
        "expected_tools": ["wikipedia"],
        "description": "A widely debunked myth that can be addressed with scientific consensus from Wikipedia."
    },
    {
        "claim": "5G technology is responsible for the spread of COVID-19.",
        "expected_tools": ["wikipedia"],
        "description": "False claim mixing science and public health; Wikipedia is appropriate to clarify."
    },
    {
        "claim": "Climate change is primarily caused by human activities such as burning fossil fuels.",
        "expected_tools": ["wikipedia"],
        "description": "A scientifically supported statement; Wikipedia explains the current consensus."
    },
    {
        "claim": "The Holocaust never happened.",
        "expected_tools": ["wikipedia"],
        "description": "Holocaust denial is false and can be addressed with historical facts from Wikipedia."
    },
    {
        "claim": "The Great Wall of China is visible from space with the naked eye.",
        "expected_tools": ["wikipedia"],
        "description": "A widely believed myth that Wikipedia can clarify as false."
    },
    {
        "claim": "Dinosaurs and humans coexisted on Earth.",
        "expected_tools": ["wikipedia"],
        "description": "False claim that contradicts paleontological evidence; best resolved with Wikipedia."
    },
    {
        "claim": "The Earth revolves around the Sun once every 365.25 days.",
        "expected_tools": ["wikipedia"],
        "description": "Scientific fact; Wikipedia is suitable for confirming celestial mechanics."
    },
    {
        "claim": "The pyramids of Egypt were built by aliens.",
        "expected_tools": ["wikipedia"],
        "description": "Conspiracy theory about ancient history; Wikipedia provides archaeological evidence."
    },
    {
        "claim": "The COVID-19 virus originated in a Chinese lab and was released intentionally.",
        "expected_tools": ["wikipedia"],
        "description": "A highly controversial and often politicized claim; Wikipedia can provide balanced context."
    },
    {
        "claim": "Bill Gates owns the patent for COVID-19 vaccines.",
        "expected_tools": ["wikipedia"],
        "description": "False attribution of vaccine patents; Wikipedia can be used to trace factual patent ownership."
    },
    {
        "claim": "The U.S. Civil War was primarily fought over states' rights, not slavery.",
        "expected_tools": ["wikipedia"],
        "description": "A revisionist claim that Wikipedia addresses with mainstream historical consensus."
    },
    {
        "claim": "The polio vaccine eradicated polio in most parts of the world.",
        "expected_tools": ["wikipedia"],
        "description": "Supported public health claim; Wikipedia has verified historical data."
    },
    {
        "claim": "Walt Disney was cryogenically frozen after his death.",
        "expected_tools": ["wikipedia"],
        "description": "Urban legend; Wikipedia provides factual information about his death."
    },
    {
        "claim": "The Flat Earth theory is supported by modern science.",
        "expected_tools": ["wikipedia"],
        "description": "Scientific misinformation; Wikipedia can clearly disprove this claim."
    },
    {
        "claim": "Marie Antoinette said, 'Let them eat cake.'",
        "expected_tools": ["wikipedia"],
        "description": "Misattributed historical quote; Wikipedia can clarify its origins and accuracy."
    },
    {
        "claim": "Christopher Columbus discovered America in 1492.",
        "expected_tools": ["wikipedia"],
        "description": "True in a limited Eurocentric context; Wikipedia provides nuance."
    },
    {
        "claim": "Albert Einstein failed math as a student.",
        "expected_tools": ["wikipedia"],
        "description": "Popular myth; Wikipedia offers accurate biographical information."
    },
    {
        "claim": "The Spanish flu pandemic killed more people than World War I.",
        "expected_tools": ["wikipedia"],
        "description": "Historically accurate claim; Wikipedia can verify statistics."
    },
    {
        "claim": "Napoleon Bonaparte was extremely short for his time.",
        "expected_tools": ["wikipedia"],
        "description": "Common misconception; Wikipedia clarifies historical context and measurements."
    }
]
