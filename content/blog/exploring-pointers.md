---
title: "Exploring Pointers"
slug: "exploring-pointers"
section: "programming-concepts"
datePublished: "2024-04-01T13:30:41.898Z"
dateUpdated: "2026-07-03T14:17:27.000Z"
description: "Demystify pointers in C programming with this beginner's guide. Learn pointer syntax, memory management, pointer arithmetic, dynamic allocation, function po"
seoTitle: "Mastering Pointers in C: A Beginner's Guide to Memory Management"
tags: ["c", "pointers", "memory-management", "pointers-in-c"]
cover: "img/exploring-pointers/c911090b1349.webp"
coverAlt: ""
hashnode: {"cuid": "clugzn5nu000808l49fxi74eo", "url": "https://sukalyanroy.hashnode.dev/exploring-pointers"}
---

### Pointers

Pointers are an important aspect of learning programming.

It's a part of every 101 course and used in almost every major algorithm or data structure under the hood for greater performance.

it's good to have a basic understanding of pointers, even though you might not need to use them in your software job directly.

These are a slightly edited version of my own notes when I was learning them a few months ago during my college studies.

In the most basic of terms, a pointer is a variable that stores the memory location of a particular piece of data. We can further hold a pointer to a pointer on and on, but that's not immediately important.

| Syntax | Meaning |
| --- | --- |
| `int x` | An integer value |
| `&x` | The address of `x` |
| `int *p` | A pointer to an integer |
| `p = &x` | Store `x`'s address in `p` |
| `*p` | The value at the address stored in `p` |

1.  Pointers are initialized by using `dataType *pointerVariableName;` .Value is assigned using the `&` or "AddressOf" Operator as follows:  
    `pointerVariable = &anotherVariable` After which the pointer stores the memory address of the concerned variable.
    
2.  We can use `*pointerVariable` to "Dereference" it. This just means that when we write `*pointerVariable`, it refers to the **Value** at the location which the pointer stores. Thus if variable `a` = 5 and `p = &a`, then `*p` = 5. We can assign values to declared but non initialized variables using the following
    
    ```c
    int a;
    int *p = &a;
    *p = 5;
    // Then if we print a we get value to be 5
    ```
    
3.  We we increment a pointer `n` , it does not change by `n` but instead by `sizeOfDatatypeElement * n` Thus by incrementing a integer type pointer by one, we change the memory location value of it by `1*4` bytes because each integer type variable takes 4 bytes in the memory.
    
    We can only increment or decrement pointers. No other arithmetic is allowed for pointers.
    
4.  The `void` pointer. We can declare a void type pointer to store the starting memory location of values of any type. We don't need to do any typecasting to store the address in it.  
    The problem is that we cannot do pointer arithmetic or dereference this pointer as the compiler does not know how far the value goes, which it does if the type is specified. We can only store and retrieve the starting address.
    
5.  To use pointers to pointers or pointers to pointers to pointers and so on upto n layers. We use `dataType ***...n variableName`. For example `int **q = &p` stores the address of pointer variable `p` in another pointer variable `q`.
    
6.  C by default uses `call by value`. This means that whenever a function is called, a copy of the arguments is sent over. All this happens in the Stack part of the memory and once the function is done executing, that part of the stack is cleared up.
    
    Now this is not a problem if we are using Global Variables as they have a separate space in the memory.
    
    But if we want to use functions to change a local variable, without reassigning it explicitly, we need to do a `Call by Reference` where we send the address of the variables to be changed rather than the copy of their values which is done by default. For example, the code to increment a local variable `a` by 1 using a function Increment can be written as `Increment(&a);` and the function itself would be `void Increment(int *p){ (*p) = (*p) + 1; }`
    
7.  **Using in Arrays**  
    An array is a contiguous block of memory having the same datatype. So when we create an array, it just tells us the type and the size, that is how many elements. Just the Array name gives us the Base address of the Array.  
    `&A[0] == &A == A` all three are the same. and `*A == A[0] == *A[0]` are all the same.
    
    We can get the nth element of an array in many ways, `A[n] == *(A+n) == n[A]`
    
    **We cannot use Pointer Arithmetic on Array Names.**
    
8.  Arrays are always passed by reference.
    
9.  Strings are nothing but character arrays in C, and just like Array pointers cannot be changed, so the same applies here.
    
10.  Multidimensional Arrays  
     2D arrays can be declared as `A[i][j]` but also as `*p[j] = &A;` gives you `A[0][j]`. And you cannot assign array addresses to pointers without doing this specific step. Similarly, `B[i][j]` = `*(B[i] + j)` = `*(*(B+i) + j)`
     
11.  When Passing a multidimensional array as a function argument, The formal argument must be `variableName[]`, and all other third brackets for the dimension must have the accurate dimension specified. For example a `C[3][2][2]` array would have a formal argument of `A[][2][2]`.
     
12.  Dynamic Memory Allocation When we use local variables and function calls, they are stored in the Stack part of the memory. But that is fixed when the program starts. If we want to allocate memory as needed during the runtime, we need to store the stuff in the Heap Part of the memory.
     
     To do that we must use functions like malloc() used as  
     `int *p = (int*)malloc(sizeOf(int));` and we have to typecast, as malloc returns a void pointer. If there is no memory left to allocate, malloc returns NULL.
     
     calloc() realloc() are similar functions, check them out when needed.
     
     **free()** When we reassign a pointer, the previous value on the heap is still unchanged, and can be mistakenly or maliciously accessed. To prevent this, we must use this function to free that part of memory once the work of that value is over
     
     ![](img/exploring-pointers/cf908f45860f.webp)
     
     .  
     Note: The Memory stack actually is an implementation of the Stack Data Structure but the Heap has nothing to do with the same named Data Structure. Also, this will start making more sense once you study Assembly and realize how C is just an advanced layer on top of it.
     

#### Function pointers

Just like arrays are contiguous blocks of memory storing a particular type of value, functions can be considered a set of instructions in the memory. When we use function pointers, it points to the first instruction of that function in the memory. We declare a function pointer as follows

```C
returnType functionName(Arguments1,arg2...){
body
}

int main(){
returnType (*p)(datatypeOfArgument1,...);
p = &functionName;
// Then to call the function
c = (*p)(argument1,....);
}
```

for example, the following code:

![](img/exploring-pointers/cac507525153.webp)

## Check this out

This [video](https://www.youtube.com/watch?v=zuegQmMdy8M&pp=ygUNcG9pbnRlcnMgaW4gQw%3D%3D) is my main resource while learning, and the screenshots are taken from here as well.