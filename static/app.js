const messageInput =
    document.getElementById("messageInput");

const chatForm =
    document.getElementById("chatForm");

const messages =
    document.getElementById("messages");

const welcome =
    document.getElementById("welcome");

const sendButton =
    document.getElementById("sendButton");

const fileInput =
    document.getElementById("fileInput");

const uploadButton =
    document.getElementById("uploadButton");

const knowledgePanel =
    document.getElementById("knowledgePanel");

const knowledgeTab =
    document.getElementById("knowledgeTab");

const closeKnowledge =
    document.getElementById("closeKnowledge");

const dropZone =
    document.getElementById("dropZone");

const documentList =
    document.getElementById("documentList");

const documentCount =
    document.getElementById("documentCount");

const chunkCount =
    document.getElementById("chunkCount");

const connectionDot =
    document.getElementById("connectionDot");

const connectionText =
    document.getElementById("connectionText");

const clearBtn =
    document.getElementById("clearBtn");

const newChatBtn =
    document.getElementById("newChatBtn");

const toast =
    document.getElementById("toast");

const uploadPreview =
    document.getElementById("uploadPreview");


/* =====================================================
   TOAST
===================================================== */

function showToast(message) {

    toast.textContent = message;

    toast.classList.add("show");

    setTimeout(() => {

        toast.classList.remove("show");

    }, 3000);
}


/* =====================================================
   AUTO RESIZE
===================================================== */

messageInput.addEventListener(
    "input",
    () => {

        messageInput.style.height = "auto";

        messageInput.style.height =
            Math.min(
                messageInput.scrollHeight,
                150
            ) + "px";
    }
);


/* =====================================================
   ADD MESSAGE
===================================================== */

function addMessage(
    role,
    text,
    sources = []
) {

    welcome.style.display = "none";

    const message =
        document.createElement("div");

    message.className =
        `message ${role}`;

    const avatar =
        document.createElement("div");

    avatar.className =
        "message-avatar";

    avatar.textContent =
        role === "user"
            ? "YOU"
            : "✦";

    const content =
        document.createElement("div");

    content.className =
        "message-content";

    const name =
        document.createElement("div");

    name.className =
        "message-name";

    name.textContent =
        role === "user"
            ? "You"
            : "Nexus AI";

    const bubble =
        document.createElement("div");

    bubble.className =
        "message-bubble";

    bubble.textContent =
        text;

    content.appendChild(name);

    content.appendChild(bubble);


    if (
        role === "assistant" &&
        sources.length > 0
    ) {

        const sourceContainer =
            document.createElement("div");

        sourceContainer.className =
            "sources";

        sources.forEach(
            source => {

                const sourceElement =
                    document.createElement("div");

                sourceElement.className =
                    "source";

                sourceElement.innerHTML =
                    `
                    <strong>
                        📄 ${escapeHtml(source.filename)}
                    </strong>
                    · Chunk ${source.chunk}
                    `;

                sourceContainer.appendChild(
                    sourceElement
                );
            }
        );

        content.appendChild(
            sourceContainer
        );
    }


    message.appendChild(avatar);

    message.appendChild(content);

    messages.appendChild(message);

    scrollToBottom();
}


/* =====================================================
   ESCAPE HTML
===================================================== */

function escapeHtml(text) {

    const div =
        document.createElement("div");

    div.textContent = text;

    return div.innerHTML;
}


/* =====================================================
   TYPING
===================================================== */

function showTyping() {

    const message =
        document.createElement("div");

    message.className =
        "message assistant";

    message.id =
        "typingMessage";

    message.innerHTML =
        `
        <div class="message-avatar">
            ✦
        </div>

        <div class="message-content">

            <div class="message-name">
                Nexus AI
            </div>

            <div class="message-bubble">

                <div class="typing">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>

            </div>

        </div>
        `;

    messages.appendChild(message);

    scrollToBottom();
}


function removeTyping() {

    const typing =
        document.getElementById(
            "typingMessage"
        );

    if (typing) {

        typing.remove();
    }
}


/* =====================================================
   SCROLL
===================================================== */

function scrollToBottom() {

    const chat =
        document.querySelector(
            ".chat-section"
        );

    chat.scrollTop =
        chat.scrollHeight;
}


/* =====================================================
   SEND MESSAGE
===================================================== */

async function sendMessage(question) {

    question =
        question.trim();

    if (!question)
        return;


    addMessage(
        "user",
        question
    );

    messageInput.value = "";

    messageInput.style.height =
        "auto";

    sendButton.disabled = true;

    showTyping();


    try {

        const response =
            await fetch(
                "/api/chat",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        message: question
                    })
                }
            );


        const data =
            await response.json();


        removeTyping();


        if (!data.success) {

            addMessage(
                "assistant",
                "⚠️ " +
                (
                    data.error ||
                    "Something went wrong."
                )
            );

            return;
        }


        addMessage(
            "assistant",
            data.answer,
            data.sources || []
        );


    } catch (error) {

        removeTyping();

        addMessage(
            "assistant",
            "⚠️ Could not connect to the NEXUS server."
        );

        console.error(error);

    } finally {

        sendButton.disabled =
            false;

        messageInput.focus();
    }
}


/* =====================================================
   FORM
===================================================== */

chatForm.addEventListener(
    "submit",
    event => {

        event.preventDefault();

        sendMessage(
            messageInput.value
        );
    }
);


/* =====================================================
   ENTER KEY
===================================================== */

messageInput.addEventListener(
    "keydown",
    event => {

        if (
            event.key === "Enter" &&
            !event.shiftKey
        ) {

            event.preventDefault();

            chatForm.requestSubmit();
        }
    }
);


/* =====================================================
   QUICK SUGGESTIONS
===================================================== */

document.querySelectorAll(
    ".suggestion"
).forEach(
    button => {

        button.addEventListener(
            "click",
            () => {

                const question =
                    button.dataset.question;

                sendMessage(question);
            }
        );
    }
);


/* =====================================================
   KNOWLEDGE PANEL
===================================================== */

knowledgeTab.addEventListener(
    "click",
    () => {

        knowledgePanel.classList.add(
            "open"
        );

        loadDocuments();
    }
);


closeKnowledge.addEventListener(
    "click",
    () => {

        knowledgePanel.classList.remove(
            "open"
        );
    }
);


/* =====================================================
   UPLOAD BUTTON
===================================================== */

uploadButton.addEventListener(
    "click",
    () => {

        fileInput.click();
    }
);


fileInput.addEventListener(
    "change",
    () => {

        if (fileInput.files.length > 0) {

            uploadFiles(
                Array.from(
                    fileInput.files
                )
            );
        }
    }
);


/* =====================================================
   DRAG & DROP
===================================================== */

[
    "dragenter",
    "dragover"
].forEach(
    eventName => {

        dropZone.addEventListener(
            eventName,
            event => {

                event.preventDefault();

                dropZone.classList.add(
                    "dragging"
                );
            }
        );
    }
);


[
    "dragleave",
    "drop"
].forEach(
    eventName => {

        dropZone.addEventListener(
            eventName,
            event => {

                event.preventDefault();

                dropZone.classList.remove(
                    "dragging"
                );
            }
        );
    }
);


dropZone.addEventListener(
    "drop",
    event => {

        const files =
            Array.from(
                event.dataTransfer.files
            );

        uploadFiles(files);
    }
);


/* =====================================================
   UPLOAD FILES
===================================================== */

async function uploadFiles(files) {

    const allowed =
        [
            "application/pdf",
            "text/plain",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ];


    for (const file of files) {

        uploadPreview.innerHTML =
            `
            <div class="upload-chip">
                ⏳ Indexing ${escapeHtml(file.name)}...
            </div>
            `;


        const formData =
            new FormData();

        formData.append(
            "file",
            file
        );


        try {

            const response =
                await fetch(
                    "/api/upload",
                    {
                        method: "POST",
                        body: formData
                    }
                );


            const data =
                await response.json();


            if (!data.success) {

                showToast(
                    data.error ||
                    "Upload failed."
                );

                continue;
            }


            showToast(
                `${file.name} indexed successfully.`
            );


        } catch (error) {

            showToast(
                "Upload failed."
            );

            console.error(error);
        }
    }


    uploadPreview.innerHTML = "";

    fileInput.value = "";

    await loadDocuments();

    await checkHealth();
}


/* =====================================================
   LOAD DOCUMENTS
===================================================== */

async function loadDocuments() {

    try {

        const response =
            await fetch(
                "/api/documents"
            );

        const data =
            await response.json();


        documentCount.textContent =
            data.total_documents;

        chunkCount.textContent =
            data.total_chunks;


        if (
            !data.documents ||
            data.documents.length === 0
        ) {

            documentList.innerHTML =
                `
                <div class="empty-files">
                    No documents indexed yet.
                </div>
                `;

            return;
        }


        documentList.innerHTML = "";


        data.documents.forEach(
            document => {

                const item =
                    document.createElement(
                        "div"
                    );

                item.className =
                    "document";

                item.innerHTML =
                    `
                    <div class="file-icon">
                        📄
                    </div>

                    <div style="min-width:0">

                        <div class="file-name">
                            ${escapeHtml(
                                document.filename
                            )}
                        </div>

                        <div class="file-meta">
                            ${document.chunks}
                            knowledge chunks
                        </div>

                    </div>
                    `;

                documentList.appendChild(
                    item
                );
            }
        );


    } catch (error) {

        console.error(error);
    }
}


/* =====================================================
   HEALTH
===================================================== */

async function checkHealth() {

    try {

        const response =
            await fetch(
                "/api/health"
            );

        const data =
            await response.json();


        if (data.ollama) {

            connectionDot.classList.remove(
                "offline"
            );

            connectionText.textContent =
                "Ollama connected";

        } else {

            connectionDot.classList.add(
                "offline"
            );

            connectionText.textContent =
                "Ollama offline";
        }


        documentCount.textContent =
            data.documents;

        chunkCount.textContent =
            data.chunks;


    } catch (error) {

        connectionDot.classList.add(
            "offline"
        );

        connectionText.textContent =
            "Server offline";
    }
}


/* =====================================================
   CLEAR DATABASE
===================================================== */

clearBtn.addEventListener(
    "click",
    async () => {

        const confirmed =
            confirm(
                "Delete all documents and knowledge chunks?"
            );

        if (!confirmed)
            return;


        try {

            const response =
                await fetch(
                    "/api/clear",
                    {
                        method: "DELETE"
                    }
                );


            const data =
                await response.json();


            if (data.success) {

                messages.innerHTML = "";

                welcome.style.display =
                    "block";

                await loadDocuments();

                showToast(
                    "Knowledge base cleared."
                );
            }


        } catch (error) {

            showToast(
                "Could not clear knowledge base."
            );
        }
    }
);


/* =====================================================
   NEW CHAT
===================================================== */

newChatBtn.addEventListener(
    "click",
    () => {

        messages.innerHTML = "";

        welcome.style.display =
            "block";

        messageInput.value = "";

        messageInput.focus();
    }
);


/* =====================================================
   INITIALIZE
===================================================== */

(async function init() {

    await checkHealth();

    await loadDocuments();

    messageInput.focus();

})();