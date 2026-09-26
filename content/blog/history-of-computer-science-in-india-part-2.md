---
title: "History of computer science in india Part 2"
slug: "history-of-computer-science-in-india-part-2"
section: "unsung-bits"
seriesOrder: 0
datePublished: "2026-07-30T06:57:07.783Z"
description: "This series explores foundational Indian computing contributions that are often omitted from standard curricula."
descriptionSource: "excerpt"
tags: ["algorithms", "programming-blogs", "computer-science", "india", "history-of-computing"]
cover: "img/history-of-computer-science-in-india-part-2/6578db2a59d4.webp"
coverAlt: ""
hashnode: {"cuid": "cms75v3jf000009i50d7x7qkr", "url": "https://sukalyanroy.hashnode.dev/history-of-computer-science-in-india-part-2"}
---

## TL;DR

*   This series explores foundational Indian computing contributions that are often omitted from standard curricula.
    
*   Each post covers a single idea in depth, from ancient algorithms to modern digital infrastructure.
    
*   Includes runnable code, deep historical context, and explicit caveats separating fact from myth.
    
*   The goal is to highlight rigorous research, not just the well-known IT services business story.
    

> **Learning status:** This introductory post sets the stage for a series of technical deep dives. No code in this specific post, but subsequent posts will include runnable demos in Python. The series can be read in any order.

A few weeks ago I published a post called [The Indian Computing Story We Were Not Taught](https://casuallyoverthinking.substack.com/p/the-indian-computing-story-we-were). I wrote it because I was finishing a Computer Engineering degree and noticed I could name every Western pioneer my syllabus put in front of me (Babbage, Boole, Turing) and almost nobody from the place I was sitting in while I studied them. The names I learned were real and the contributions were real; that's not the complaint. But nobody says "and there's more we're skipping." You just absorb a shape of history where the interesting things happened elsewhere and arrived here as imports.

So I went digging. The post that came out of it tried to hold the whole thing in one breath: from an HEC 2M wheeled into Kolkata in 1955 to a 105-billion-parameter model trained in India earlier this year. TIFRAC, ECIL, the morning IBM walked out in 1977, Infosys starting on $250, Bhatkar's PARAM machines, all of it.

Here's the problem with a survey, though. It can only point at things. Somewhere in that sprint, the AKS primality test got exactly one sentence and three names. UPI got flattened into a single number ([22 billion transactions in a month](https://www.npci.org.in/what-we-do/upi/product-statistics)), and then I had to move on, because there were still forty years of history waiting. You can't stop and show someone *how* AKS actually decides a number is prime when there's 10 other things to talk about.

At the end of that post I promised to come back and do the specific pieces properly, one at a time.

## What I actually want to do here

One idea per post.

Each post takes a single idea: where it came from, what problem someone was actually staring at, how it works (with a worked example and code you can clone and run), and where the popular telling of it is wrong.

Reading that an algorithm "corrects errors" is one thing. Watching it rebuild a byte you deliberately corrupted, or decide a 40-digit number is prime, or find the cheapest plan in a knot of constraints, is a different thing. So every post ships with a small demo you can actually run, in a folder you could fork and break and learn from.

## What I mean by "underrated"

Some of these are famous inside their own field: an optimization researcher does not need me to introduce them to Karmarkar, and no theoretical computer scientist has failed to hear of the AKS test.

"Underrated" here means the contribution is bigger than its reach into general awareness, and usually bigger than its reach into the *Indian* awareness of itself. We celebrate the IT-services boom and the unicorns.

We are much quieter about the fact that a deterministic polynomial-time primality test (a clean answer to a genuinely old question) came out of an IIT Kanpur office in 2002, by people who were students at the time.

There's a reason this particular blind spot exists, and it's not just colonial-hangover syllabus design. India mostly tells its own computing story as a *business* story: the services boom, the export numbers, the campus placements, the unicorn count.

A founder who built a billion-dollar services company is a national figure. The trio who put PRIMES in P are a trivia answer.

I'm not mocking the business story; I'm saying it became the *whole* story, and the residue is a generation of engineers (me included, until recently) who could recite the founding year of three IT companies and not one original algorithm that came out of the same country.

The other thing I mean: I'm reaching past "computing in India" to "computing by Indians and people of Indian origin," which are different sets that overlap messily. Karmarkar did his famous work at Bell Labs in New Jersey.

Pāṇini predates the idea of a nation called India by a couple of thousand years.

A story that only counted machines physically built on Indian soil would miss most of what's actually interesting, so I'm not going to draw the boundary there. I'll tell you where each person was and let you decide what to do with it.

## Why I care about this

I'm Indian, and I think these stories are worth telling. I'm also tired of the other genre: the forwarded-message one, where ancient India invented jet engines and the internet, and every claim swells until it collapses under thirty seconds of scrutiny. That genre does the real contributions a disservice, because the moment a reader catches one inflated claim, they quietly stop believing the true ones too.

If a celebrated project flopped commercially, that's in the post because the real stories must survive the scrutiny. That's the whole reason they're worth a thousand words each instead of one line in a survey.

Case in point, and slightly embarrassing: a draft of the very first post in this series claimed Pāṇini named sixty-four earlier grammarians. He named ten. I caught it during editing but that's exactly the kind of small inflation that, stacked a hundred posts high, silently turns a real history into a forwarded message. So I check, and I cite at the point of the claim instead of dumping links at the end, and when I'm guessing I say "I'm guessing."

## How the series is laid out

It's arranged so you can read it front to back as a rough arc, from before computers existed to the infrastructure that ran the country this morning.

Note: This is the planned sequence, but this can change as I work on the individual posts. Some topics can be removed, some new ones might be added. I'll try to keep this beginning post updated after the series is finished.

It opens in the deep past, with people doing computer-science-shaped thinking with no computer in sight: Pāṇini's rule system, Piṅgala's binary combinatorics, Aryabhata's algorithm for solving equations, and the place-value notation everything else is written in. Then the foundations of working with data: Mahalanobis and C. R. Rao, whose statistics underwrite a lot of modern machine learning.

From there it moves into the work most people mean by "computer science." Error-correcting codes that repair themselves. Karmarkar's works in optimization. A run through complexity and algorithms (AKS, the PCP theorem, the Unique Games Conjecture, the two Vazirani brothers, Mulmuley's long shot at P versus NP) and then the stranger corners: computing on data that stays encrypted, quantum query complexity, the algorithm behind "people who bought this also bought." Speech recognition, decades before anyone said "Hey Siri."

Then the physical and the practical: fibre optics, the antenna math behind your WiFi, the Pentium, the USB port, the supercomputer India built after it was refused one, and the systems code running Google. A handheld built for the people the industry forgot. And finally the layer you touch daily without seeing it: Aadhaar, UPI, and the rest of India's digital public infrastructure, sharp edges included.

If there's a through-line, it's the one my last post kept circling: India's computing story gets told as a business story (the services boom, the unicorns, the placement numbers) and the research story underneath it stays in the footnotes. These posts are an attempt to pull one thing at a time out of the footnotes and look at it properly, with the code to back it up. You can read them in order, or dip in wherever a title catches you; each one stands on its own, caveats included.

The survey started in 1955. This one starts about 2,500 years before that, with a grammarian, a system of rules, and the genuinely unsettling question of whether he was, in some strange sense, writing code. That's where we begin.

See you in the next one.

Which topic are you most curious about? Let me know in the comments.