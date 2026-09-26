---
title: "What even are LLMs?"
slug: "what-even-are-llms"
section: "aiml"
datePublished: "2024-12-10T12:32:27.575Z"
dateUpdated: "2026-06-08T03:43:12.000Z"
description: "Explore the world of Large Language Models (LLMs) driving AI chatbots and their future applications, challenges, and recent advancements"
seoTitle: "Understanding Language Learning Models"
tags: ["llm", "rag"]
cover: "img/what-even-are-llms/c4e546dab5f3.jpg"
coverAlt: ""
hashnode: {"cuid": "cm4ifys3b000i0amn0f5qdulw", "url": "https://sukalyanroy.hashnode.dev/what-even-are-llms"}
---

### What exactly is an LLM?

It’s what drives ChatgGPT. No, really. That’s what an LLM is. From Chatgpt to Claude to Bing to Gemini, the technical term for these magical chatbots is a Large Language Model (LLM).

For a clear first impression, watching [This video](https://www.youtube.com/watch?v=zjkBMFhNj_g%5D\(https://www.youtube.com/watch?v=zjkBMFhNj_g\)) is essential; barely anyone else can explain LLMs like Andrej.  
Consider this post as simultaneously a TLDR of the video and a somewhat deeper dive into the topics through supplementary articles.

And if you're curious about Neural networks in general, you should check out another post of mine, [here](/blog/understanding-neural-networks/)

To summarize the idea, LLMs or Large Language Models are the product of a new way of thinking about text processing.

It works on the fairly new attention-based transformer architecture to encode all its training data into a set of internal representations. Given how the training data is a several terabyte scrape of the internet, one could, as Andrej explains it, think of it like a semantic, lossy compression of the internet itself.

These representations work like a probabilistic "next word predictor" of sorts, which takes in some context and generates new words. It then takes those words back into it's context and repeats this process for a set amount of iterations.

The training step is the actual heavy-duty process and something that most of us do not need to care about, as users of the API or the open-weight/open-source files/models.

Speaking of the architecture itself, here is a diagram from the paper "Attention is all you need":

![Diagram of the Transformer model architecture, showing the encoder and decoder stacks. Each consists of layers of multi-head attention and feed-forward neural networks, with add and norm steps. Positional encoding is applied to input and output embeddings. The decoder includes masked multi-head attention. Output probabilities are obtained after a linear layer and softmax.](img/what-even-are-llms/11274d0e7dbb.webp)

this has a lot of parts and if there is enough demand for this, I will immediately start working on my own explanation of this seminal paper.

### What's the reversal curse?

The reversal curse is the tendency of LLMs to not have bidirectional reasoning among it's internal logic.

(Note: This is mostly true for Autoencoder models, which happen to be the most common type in use. For stuff like Google’s BERT, this might be less of a problem)

It means that, if it is trained on sentences like `X is Y`, then it will learn precisely that, but it won't be able to answer questions like "What is Y".

More precisely, if a model is trained mostly on data that says `name is description` Then it won't be able to reason that `description refers to name`.

For example: if it is trained on `Rabindranath Tagore was the first asian to win the Nobel prize`.

If you ask who Rabindranath Tagore is, it will respond about the Nobel Prize.

But if you ask "Who was the first Asian to win a Nobel Prize?" then the model won't be able to answer.

Now to be clear about this, for my particular example, there are countless examples of both the former and the latter form of this bit of data on the internet, so an average model trained on it will be able to answer it.

**But** there are many many cases where both the direct and indirect form of the knowledge will not be present. For most cases it won't be sufficiently present. So the model will fail here.

There have been several attempts to retrain or finetune models to work around this but with no noticeable improvement so far.

Do humans have something similar? think about the last time you tried to rattle out the alphabet or a random poem in reverse.

### How might one make their own transformers?

there are several tutorials online, but as a principle, you will start by learning about the transformer architecture and attention mechanism, followed by a fair amount of programming. Soon, I will be trying out the best tutorial on the internet by Andrej Karpathy and write up my journey as I go. Stay tuned for that.

### Intro to finetuning models

Once the major training period on vast amount of data is done(quantity over quality), we have what is called a base model.

This base model now forms the foundation for different models in use. However, this base model by itself is useless, we need to train these models further on the specific use case we are hoping to use it for. We need to "finetune" it using domain or interaction specific data. (quality over quantity)

Often this data comes from proprietary sources or is done manually by humans who write up sample conversations (There are outsourcing companies for this like ScaleAi). In many cases such as that of Chatgpt, it uses user ratings on given responses, asks the users about alternatives to internally keep updating the model's behavior.

Even though it is cheaper than full fledged base model creation; Effective finetuning takes a nontrivial amount of hardware which is often not found on Low end or budget Desktops and laptops. In that case, online providers like Google Colab is a relatively cheap and effective solution to experiment with this.

I have delved into some aspects of finetuning before when working on my chatbot for a hackathon. Still, there is a lot i need to learn myself before I can come up with a detailed exposition on this topic. Stay tuned for that.

### Breaking and Toying with LLMs

There are many ways to bend LLMs to your will, most of them relevant to Online or API based Models because they have the most restrictions, whereas the Open source models are much more open about content.

Disclaimer: There are many many more that I discovered from reading research papers and articles online, which i do not feel comfortable sharing for the fear of misuse. I myself shall always refrain from using these LLMs for malicious purposes.

Some of those include things like

1.  Jailbreaks: essentially roleplaying with the LLM in a way to convince it that it has no restrictions.
    
2.  Asking your "forbidden" question in languages other than english, because even though the models are trained on many different languages, most of the security measures are implemented in english.
    
3.  Prompt injection attacks: Used by websites to gain control over models that actively query data from sites. Usually these are instructions for the model, written in white text inside the web pages so that it is invisible to the users, but often these are effective enough that it can change the behaviour of the responses.
    

### Recent Developments

In his book Thinking fast and slow, Daniel Kahneman explains his theory about two systems in the human brain. System 1 is intuitive, fast(split second), not correct all the time but good enough. It is in many ways important for us to survive our day to day lives without overthinking everything.

System 2 on the other hand, is all about effortful thinking, deliberating, analysis and decision making. This is the system of our brain that leads to nontrivial developments in human knowledge, which helps us to make the really important decisions in our life.

In recent times, models like chatgpt have been slowly incorporating more System 2 thinking in their models, so that instead of acting like next word generators with no thinking, it actually does some "thinking" internally which is not shown to the user, before the final answer is given. Now according to my current understanding, this is just some form of self prompting using tried and tested prompt engineering techniques implemented directly into the model and not some philosophical or biological equivalent of actual human thinking.

### Future prospects?

There are some researchers working on making LLMs collaborate with each other. Where a general purpose model starts working on something, and based on certain "switches" they decide when to ask an expert model for more elaboration.

In this way, most of the work is done by a lightweight general puporse model, and the detailed finetuned ones are only called when a depth of data is needed.

#### New paradigm in Operating Systems

There is a growing interest in the application of LLMs as the central hub or kernel that would sit at the centre of a next generation Operating system. Instead of traditional Operating systems, you would have a direct interface to the LLM and it will orchestrate all your daily needs. Almost like a real life Jarvis.

there are many implementations that "sort of" work today and many more research papers detailing different approaches to balance the load between traditional OS and LLM based solutions.

### References and further reading

To wrap it all up, i’ve put forward the most succinct explanations of the basics I could, and there are many great resources online to learn more.

Do check these links out, and drop all your suggestions for further posts or any questions related to the content covered down in the comment section.

[https://www.lesswrong.com/posts/SCqDipWAhZ49JNdmL/paper-llms-trained-on-a-is-b-fail-to-learn-b-is-a](https://www.lesswrong.com/posts/SCqDipWAhZ49JNdmL/paper-llms-trained-on-a-is-b-fail-to-learn-b-is-a) This goes deeper into the reversal curse.

[https://news.mit.edu/2024/enhancing-llm-collaboration-smarter-more-efficient-solutions-0916](https://news.mit.edu/2024/enhancing-llm-collaboration-smarter-more-efficient-solutions-0916) This talks about inter LLM collaborations for more effective expert knowledge.

The following two delve into the topic of LLM OS.

[https://community.aws/content/2eojjD2E7TBgPFJmB2FGAtrSSBh/the-rise-of-the-llm-os-from-aios-to-memgpt-and-beyond](https://community.aws/content/2eojjD2E7TBgPFJmB2FGAtrSSBh/the-rise-of-the-llm-os-from-aios-to-memgpt-and-beyond)

[https://mansour-damanpak.medium.com/llm-os-and-software-2-0-the-dawn-of-a-new-computing-era-12d59a007ef8](https://mansour-damanpak.medium.com/llm-os-and-software-2-0-the-dawn-of-a-new-computing-era-12d59a007ef8)