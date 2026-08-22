document.addEventListener("DOMContentLoaded", function () {
    const chatRoot = document.querySelector("[data-chat-root]");
    if (!chatRoot) {
        // Setup search on conversation list page if present
        const searchInput = document.getElementById("conv-search-input");
        const items = document.querySelectorAll("[data-conv-item]");
        if (searchInput && items.length > 0) {
            searchInput.addEventListener("input", function () {
                const query = this.value.toLowerCase().trim();
                items.forEach(function (item) {
                    const name = item.getAttribute("data-conv-name") || "";
                    const service = item.getAttribute("data-conv-service") || "";
                    if (name.includes(query) || service.includes(query)) {
                        item.style.display = "flex";
                    } else {
                        item.style.display = "none";
                    }
                });
            });
        }
        return;
    }

    const conversationId = chatRoot.dataset.conversationId;
    const currentUserId = String(chatRoot.dataset.userId || "");
    const currentUserName = chatRoot.dataset.userName || "You";
    const otherPartyName = chatRoot.dataset.otherName || "Participant";

    const statusElement = document.getElementById("chat-connection-status");
    const messagesContainer = document.getElementById("chat-messages");
    const chatForm = document.getElementById("chat-form");
    const messageInput = document.getElementById("chat-message-input");
    const sendButton = document.getElementById("chat-send-button");
    const errorBanner = document.getElementById("chat-error-banner");

    // Attachment Components
    const plusMenuBtn = document.getElementById("pv-plus-menu-btn");
    const attachmentMenu = document.getElementById("pv-attachment-menu");
    const attachImageBtn = document.getElementById("pv-attach-image-btn");
    const attachVideoBtn = document.getElementById("pv-attach-video-btn");
    const fileImageInput = document.getElementById("pv-file-image-input");
    const fileVideoInput = document.getElementById("pv-file-video-input");
    const previewBar = document.getElementById("pv-attachment-preview-bar");
    const previewThumbnail = document.getElementById("pv-preview-thumbnail-container");
    const previewFilename = document.getElementById("pv-preview-filename");
    const previewFilesize = document.getElementById("pv-preview-filesize");
    const previewRemoveBtn = document.getElementById("pv-preview-remove-btn");

    // Typing & Floating Pill
    const typingIndicator = document.getElementById("pv-typing-indicator");
    const typingText = document.getElementById("pv-typing-text");
    const scrollBottomPill = document.getElementById("pv-scroll-bottom-pill");
    const newMsgCountSpan = document.getElementById("pv-new-msg-count");

    // Booking Drawer Components
    const infoToggleBtn = document.getElementById("pv-info-toggle-btn");
    const bookingDrawer = document.getElementById("pv-booking-drawer");
    const drawerBackdrop = document.getElementById("pv-booking-drawer-backdrop");
    const closeDrawerBtn = document.getElementById("pv-close-drawer-btn");

    // Sidebar search
    const searchInput = document.getElementById("conv-search-input");
    const convItems = document.querySelectorAll("[data-conv-item]");

    if (searchInput && convItems.length > 0) {
        searchInput.addEventListener("input", function () {
            const query = this.value.toLowerCase().trim();
            convItems.forEach(function (item) {
                const name = item.getAttribute("data-conv-name") || "";
                const service = item.getAttribute("data-conv-service") || "";
                if (name.includes(query) || service.includes(query)) {
                    item.style.display = "flex";
                } else {
                    item.style.display = "none";
                }
            });
        });
    }

    if (!conversationId) {
        return;
    }

    let unreadIncomingCount = 0;
    let selectedFile = null;
    let typingTimer = null;
    let isTypingActive = false;
    let peerTypingTimeout = null;

    // Scroll to bottom on initial load
    if (messagesContainer) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function isScrolledNearBottom() {
        if (!messagesContainer) return true;
        const threshold = 120;
        const position = messagesContainer.scrollTop + messagesContainer.clientHeight;
        const bottom = messagesContainer.scrollHeight;
        return bottom - position <= threshold;
    }

    function scrollToBottom(smooth = true) {
        if (!messagesContainer) return;
        messagesContainer.scrollTo({
            top: messagesContainer.scrollHeight,
            behavior: smooth ? "smooth" : "auto",
        });
        unreadIncomingCount = 0;
        if (scrollBottomPill) {
            scrollBottomPill.classList.add("hidden");
        }
    }

    if (messagesContainer) {
        messagesContainer.addEventListener("scroll", function () {
            if (isScrolledNearBottom()) {
                unreadIncomingCount = 0;
                if (scrollBottomPill) {
                    scrollBottomPill.classList.add("hidden");
                }
            }
        });
    }

    if (scrollBottomPill) {
        scrollBottomPill.addEventListener("click", function () {
            scrollToBottom(true);
        });
    }

    // Status Pill Handler
    let statusHideTimeout = null;
    function updateStatus(state, label) {
        if (!statusElement) return;

        if (statusHideTimeout) {
            clearTimeout(statusHideTimeout);
            statusHideTimeout = null;
        }

        statusElement.textContent = label;
        statusElement.classList.remove("hidden");

        statusElement.className = "text-[10px] font-mono px-2 py-0.5 rounded border transition-colors";

        if (state === "connecting" || state === "reconnecting") {
            statusElement.classList.add("border-[#dfc38f]/40", "bg-[#dfc38f]/10", "text-[#dfc38f]");
        } else if (state === "connected") {
            statusElement.classList.add("border-[#57F1DB]/40", "bg-[#57F1DB]/10", "text-[#57F1DB]");
            statusHideTimeout = setTimeout(function () {
                statusElement.classList.add("hidden");
            }, 2500);
        } else if (state === "disconnected") {
            statusElement.classList.add("border-[#334155]", "bg-[#1E293B]", "text-[#BACAC5]");
        } else if (state === "error") {
            statusElement.classList.add("border-[#FFB4AB]/40", "bg-[#FFB4AB]/10", "text-[#FFB4AB]");
        }
    }

    function showError(messageText) {
        if (!errorBanner) return;
        errorBanner.textContent = messageText;
        errorBanner.classList.remove("hidden");
        setTimeout(function () {
            errorBanner.classList.add("hidden");
        }, 5000);
    }

    function hideError() {
        if (errorBanner) {
            errorBanner.classList.add("hidden");
        }
    }

    // WebSocket Management
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/chat/${conversationId}/`;

    let socket = null;
    let reconnectTimer = null;
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 10;
    const baseDelay = 1000;
    let isExplicitlyClosed = false;

    function connectWebSocket() {
        if (socket && (socket.readyState === WebSocket.CONNECTING || socket.readyState === WebSocket.OPEN)) {
            return;
        }

        updateStatus(reconnectAttempts > 0 ? "reconnecting" : "connecting", reconnectAttempts > 0 ? "Reconnecting..." : "Connecting...");

        try {
            socket = new WebSocket(wsUrl);
        } catch (e) {
            updateStatus("error", "Connection error");
            scheduleReconnect();
            return;
        }

        socket.onopen = function () {
            reconnectAttempts = 0;
            updateStatus("connected", "Connected");
        };

        socket.onclose = function (event) {
            updateStatus("disconnected", "Reconnecting...");

            if (isExplicitlyClosed || event.code === 4001 || event.code === 4003) {
                updateStatus("error", "Disconnected");
                return;
            }

            scheduleReconnect();
        };

        socket.onerror = function () {
            updateStatus("error", "Connection error");
        };

        socket.onmessage = function (event) {
            try {
                const data = JSON.parse(event.data);
                if (data.type === "message") {
                    handleIncomingMessage(data);
                } else if (data.type === "typing") {
                    handleIncomingTyping(data);
                } else if (data.type === "error") {
                    showError(data.message || "An error occurred.");
                }
            } catch (err) {
                console.error("Error parsing WebSocket payload:", err);
            }
        };
    }

    function scheduleReconnect() {
        if (isExplicitlyClosed || reconnectTimer) {
            return;
        }

        if (reconnectAttempts >= maxReconnectAttempts) {
            updateStatus("error", "Disconnected");
            return;
        }

        reconnectAttempts++;
        const delay = Math.min(baseDelay * Math.pow(1.5, reconnectAttempts - 1), 10000);

        reconnectTimer = setTimeout(function () {
            reconnectTimer = null;
            connectWebSocket();
        }, delay);
    }

    window.addEventListener("beforeunload", function () {
        isExplicitlyClosed = true;
        if (reconnectTimer) {
            clearTimeout(reconnectTimer);
        }
        if (socket) {
            socket.close();
        }
    });

    connectWebSocket();

    // Typing Emitter
    function emitTyping(isTyping) {
        if (!socket || socket.readyState !== WebSocket.OPEN) return;
        socket.send(
            JSON.stringify({
                type: "typing",
                is_typing: isTyping,
            })
        );
    }

    if (messageInput) {
        // Auto-expand textarea
        messageInput.addEventListener("input", function () {
            this.style.height = "auto";
            this.style.height = Math.min(this.scrollHeight, 128) + "px";

            if (!isTypingActive) {
                isTypingActive = true;
                emitTyping(true);
            }

            if (typingTimer) {
                clearTimeout(typingTimer);
            }

            typingTimer = setTimeout(function () {
                isTypingActive = false;
                emitTyping(false);
            }, 2500);
        });

        // Enter key to send, Shift+Enter for newline
        messageInput.addEventListener("keydown", function (e) {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                if (chatForm) {
                    chatForm.dispatchEvent(new Event("submit", { cancelable: true }));
                }
            }
        });
    }

    // Incoming Typing Handler
    function handleIncomingTyping(data) {
        if (String(data.sender_id) === currentUserId) return;
        if (!typingIndicator || !typingText) return;

        if (peerTypingTimeout) {
            clearTimeout(peerTypingTimeout);
            peerTypingTimeout = null;
        }

        if (data.is_typing) {
            typingText.textContent = `${data.sender_username || otherPartyName} is typing...`;
            typingIndicator.classList.remove("hidden");

            peerTypingTimeout = setTimeout(function () {
                typingIndicator.classList.add("hidden");
            }, 3500);
        } else {
            typingIndicator.classList.add("hidden");
        }
    }

    // Incoming Message Handler
    function handleIncomingMessage(data) {
        if (!messagesContainer) return;

        // Hide typing indicator immediately when message arrives
        if (typingIndicator) {
            typingIndicator.classList.add("hidden");
        }

        const isCurrentUser = String(data.sender_id) === currentUserId;

        // If current user sent this, check if an optimistic pending bubble exists
        if (isCurrentUser) {
            const pendingBubble = messagesContainer.querySelector(`[data-pending-content="${encodeURIComponent(data.content)}"]`);
            if (pendingBubble) {
                pendingBubble.removeAttribute("data-pending-content");
                if (data.message_id) {
                    pendingBubble.setAttribute("data-message-id", data.message_id);
                }
                const statusSpan = pendingBubble.querySelector(".pv-msg-status");
                if (statusSpan) {
                    statusSpan.innerHTML = `<span class="material-symbols-outlined text-[14px] text-[#57F1DB]">check</span>`;
                }
                return;
            }
        }

        // Prevent duplicate rendering
        if (data.message_id && messagesContainer.querySelector(`[data-message-id="${data.message_id}"]`)) {
            return;
        }

        // Remove empty state if present
        const emptyState = messagesContainer.querySelector("[data-empty-state]");
        if (emptyState) {
            emptyState.remove();
        }

        const wasNearBottom = isScrolledNearBottom();

        // Check if System Message
        if (data.content && data.content.startsWith("[SYSTEM]")) {
            const sysWrapper = document.createElement("div");
            sysWrapper.className = "stitch-sys-message my-4 flex flex-col items-center justify-center text-center px-4";
            if (data.message_id) {
                sysWrapper.setAttribute("data-message-id", data.message_id);
            }

            sysWrapper.innerHTML = `
                <div class="w-full max-w-md border-t border-[#334155]"></div>
                <div class="py-2 font-mono text-xs font-bold text-[#57F1DB] uppercase tracking-wider flex items-center gap-2">
                    <span class="material-symbols-outlined text-base">verified</span>
                    <span>SERVICE COMPLETED</span>
                </div>
                <p class="text-xs text-[#BACAC5] max-w-md">
                    Your service request has been marked as officially completed.
                </p>
                <div class="w-full max-w-md border-t border-[#334155] mt-2"></div>
            `;
            messagesContainer.appendChild(sysWrapper);
        } else {
            // Regular message bubble (Stitch layout)
            const wrapper = document.createElement("div");
            wrapper.className = `pv-message-row ${isCurrentUser ? "justify-end" : "justify-start"} stitch-msg-enter`;
            if (data.message_id) {
                wrapper.setAttribute("data-message-id", data.message_id);
            }
            wrapper.setAttribute("data-sender-id", data.sender_id);

            const bubbleGroup = document.createElement("div");
            bubbleGroup.className = `pv-message-group ${isCurrentUser ? "items-end" : "items-start"}`;

            let nameSpan = null;
            if (!isCurrentUser && data.sender_username) {
                nameSpan = document.createElement("span");
                nameSpan.className = "pv-message-sender text-[11px] font-mono text-[#BACAC5]";
                nameSpan.textContent = data.sender_username;
            }

            const bubble = document.createElement("div");
            bubble.className = `pv-message-bubble ${isCurrentUser ? "bg-[#4F46E5] border border-[#4338CA] text-white rounded-2xl rounded-tr-xs" : "bg-[#1E293B] border border-[#334155] text-[#DAE2FD] rounded-2xl rounded-tl-xs"} px-4 py-2.5 shadow-sm`;

            if (!isCurrentUser && data.sender_username) {
                bubble.appendChild(nameSpan);
            }

            const contentP = document.createElement("p");
            contentP.className = "text-sm whitespace-pre-wrap break-words leading-relaxed";
            contentP.textContent = data.content;
            bubble.appendChild(contentP);

            const metaDiv = document.createElement("div");
            metaDiv.className = "pv-message-meta flex items-center justify-end gap-1";

            const timeSpan = document.createElement("span");
            timeSpan.className = "text-[10px] font-mono text-[#BACAC5]";
            if (data.created_at) {
                try {
                    const dateObj = new Date(data.created_at);
                    timeSpan.textContent = dateObj.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
                } catch (e) {
                    timeSpan.textContent = data.created_at;
                }
            } else {
                timeSpan.textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
            }
            metaDiv.appendChild(timeSpan);

            if (isCurrentUser) {
                const tickSpan = document.createElement("span");
                tickSpan.className = "pv-msg-status";
                tickSpan.innerHTML = `<span class="material-symbols-outlined text-[14px] text-[#57F1DB]">check</span>`;
                metaDiv.appendChild(tickSpan);
            }

            bubble.appendChild(metaDiv);
            bubbleGroup.appendChild(bubble);
            wrapper.appendChild(bubbleGroup);
            messagesContainer.appendChild(wrapper);
        }

        // Auto-scroll or show floating pill
        if (wasNearBottom || isCurrentUser) {
            scrollToBottom(true);
        } else {
            unreadIncomingCount++;
            if (scrollBottomPill && newMsgCountSpan) {
                newMsgCountSpan.textContent = `${unreadIncomingCount} new message${unreadIncomingCount > 1 ? "s" : ""}`;
                scrollBottomPill.classList.remove("hidden");
            }
        }
    }

    // Optimistic Message Rendering
    function renderOptimisticMessage(content) {
        if (!messagesContainer) return null;

        const emptyState = messagesContainer.querySelector("[data-empty-state]");
        if (emptyState) {
            emptyState.remove();
        }

        const wrapper = document.createElement("div");
        wrapper.className = "pv-message-row flex justify-end stitch-msg-enter";
        wrapper.setAttribute("data-pending-content", encodeURIComponent(content));

        const bubbleGroup = document.createElement("div");
        bubbleGroup.className = "pv-message-group items-end";

        const bubble = document.createElement("div");
        bubble.className = "pv-message-bubble bg-[#4F46E5] border border-[#4338CA] text-white rounded-2xl rounded-tr-xs px-4 py-2.5 shadow-sm";

        const contentP = document.createElement("p");
        contentP.className = "text-sm whitespace-pre-wrap break-words leading-relaxed";
        contentP.textContent = content;
        bubble.appendChild(contentP);
        bubbleGroup.appendChild(bubble);

        const metaDiv = document.createElement("div");
        metaDiv.className = "pv-message-meta flex items-center justify-end gap-1";

        const timeSpan = document.createElement("span");
        timeSpan.className = "text-[10px] font-mono text-[#BACAC5]";
        timeSpan.textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
        metaDiv.appendChild(timeSpan);

        const statusSpan = document.createElement("span");
        statusSpan.className = "text-[#BACAC5] italic text-[10px] font-mono pv-msg-status";
        statusSpan.textContent = "Sending...";
        metaDiv.appendChild(statusSpan);

        bubble.appendChild(metaDiv);
        bubbleGroup.appendChild(bubble);
        wrapper.appendChild(bubbleGroup);
        messagesContainer.appendChild(wrapper);

        scrollToBottom(true);
        return wrapper;
    }

    function markMessageFailed(wrapper, content) {
        if (!wrapper) return;
        const bubble = wrapper.querySelector(".bg-\\[\\#4F46E5\\]");
        if (bubble) {
            bubble.classList.add("border-[#FFB4AB]");
        }
        const statusSpan = wrapper.querySelector(".pv-msg-status");
        if (statusSpan) {
            statusSpan.className = "text-[#FFB4AB] font-mono text-[10px]";
            statusSpan.innerHTML = `Failed &bull; <button type="button" class="underline hover:text-white pv-retry-btn cursor-pointer bg-transparent border-none p-0">Retry</button>`;
            const retryBtn = statusSpan.querySelector(".pv-retry-btn");
            if (retryBtn) {
                retryBtn.addEventListener("click", function () {
                    statusSpan.textContent = "Sending...";
                    statusSpan.className = "text-[#BACAC5] italic text-[10px] font-mono pv-msg-status";
                    if (bubble) {
                        bubble.classList.remove("border-[#FFB4AB]");
                    }
                    if (socket && socket.readyState === WebSocket.OPEN) {
                        socket.send(JSON.stringify({ content: content }));
                    } else {
                        setTimeout(function () {
                            markMessageFailed(wrapper, content);
                        }, 1000);
                    }
                });
            }
        }
    }

    // Attachments & Emoji Handling
    const emojiBtn = document.getElementById("pv-emoji-btn");
    const emojiMenu = document.getElementById("pv-emoji-menu");
    const emojiPicks = document.querySelectorAll(".pv-emoji-pick");

    if (emojiBtn && emojiMenu) {
        emojiBtn.addEventListener("click", function (e) {
            e.stopPropagation();
            if (attachmentMenu) attachmentMenu.classList.add("hidden");
            emojiMenu.classList.toggle("hidden");
        });

        emojiPicks.forEach(function (btn) {
            btn.addEventListener("click", function () {
                const char = this.textContent.trim();
                if (messageInput) {
                    messageInput.value += char;
                    messageInput.focus();
                }
                emojiMenu.classList.add("hidden");
            });
        });
    }

    if (plusMenuBtn && attachmentMenu) {
        plusMenuBtn.addEventListener("click", function (e) {
            e.stopPropagation();
            if (emojiMenu) emojiMenu.classList.add("hidden");
            attachmentMenu.classList.toggle("hidden");
        });

        document.addEventListener("click", function (e) {
            if (!attachmentMenu.contains(e.target) && e.target !== plusMenuBtn) {
                attachmentMenu.classList.add("hidden");
            }
            if (emojiMenu && !emojiMenu.contains(e.target) && e.target !== emojiBtn) {
                emojiMenu.classList.add("hidden");
            }
        });
    }

    if (attachImageBtn && fileImageInput) {
        attachImageBtn.addEventListener("click", function () {
            attachmentMenu.classList.add("hidden");
            fileImageInput.click();
        });
    }

    if (attachVideoBtn && fileVideoInput) {
        attachVideoBtn.addEventListener("click", function () {
            attachmentMenu.classList.add("hidden");
            fileVideoInput.click();
        });
    }

    function handleFilePicked(file, type) {
        if (!file) return;
        selectedFile = { file: file, type: type };

        if (previewBar && previewFilename && previewFilesize && previewThumbnail) {
            previewFilename.textContent = file.name;
            const sizeInKb = (file.size / 1024).toFixed(1);
            previewFilesize.textContent = `${sizeInKb} KB &bull; ${type.toUpperCase()}`;

            if (type === "image") {
                const reader = new FileReader();
                reader.onload = function (e) {
                    previewThumbnail.innerHTML = `<img src="${e.target.result}" class="h-full w-full object-cover rounded-lg" alt="Preview" />`;
                };
                reader.readAsDataURL(file);
            } else {
                previewThumbnail.innerHTML = `<span class="material-symbols-outlined text-base">videocam</span>`;
            }

            previewBar.classList.remove("hidden");
        }
    }

    if (fileImageInput) {
        fileImageInput.addEventListener("change", function () {
            if (this.files && this.files[0]) {
                handleFilePicked(this.files[0], "image");
            }
        });
    }

    if (fileVideoInput) {
        fileVideoInput.addEventListener("change", function () {
            if (this.files && this.files[0]) {
                handleFilePicked(this.files[0], "video");
            }
        });
    }

    if (previewRemoveBtn) {
        previewRemoveBtn.addEventListener("click", function () {
            selectedFile = null;
            if (fileImageInput) fileImageInput.value = "";
            if (fileVideoInput) fileVideoInput.value = "";
            if (previewBar) previewBar.classList.add("hidden");
        });
    }

    // Form Submission
    if (chatForm && messageInput) {
        chatForm.addEventListener("submit", function (e) {
            e.preventDefault();
            hideError();

            let text = messageInput.value.trim();

            if (selectedFile) {
                const fileLabel = `[Attachment: ${selectedFile.file.name}]`;
                text = text ? `${text}\n${fileLabel}` : fileLabel;
            }

            if (!text) {
                return;
            }

            // Clear inputs immediately
            messageInput.value = "";
            messageInput.style.height = "auto";
            if (selectedFile) {
                selectedFile = null;
                if (fileImageInput) fileImageInput.value = "";
                if (fileVideoInput) fileVideoInput.value = "";
                if (previewBar) previewBar.classList.add("hidden");
            }

            // Emit typing false
            if (isTypingActive) {
                isTypingActive = false;
                emitTyping(false);
            }

            // Optimistic render
            const optWrapper = renderOptimisticMessage(text);

            if (!socket || socket.readyState !== WebSocket.OPEN) {
                showError("Connecting to service messenger...");
                setTimeout(function () {
                    markMessageFailed(optWrapper, text);
                }, 1500);
                return;
            }

            try {
                socket.send(
                    JSON.stringify({
                        content: text,
                    })
                );
            } catch (err) {
                markMessageFailed(optWrapper, text);
            }
        });
    }

    // Booking Context Drawer (Slide-over)
    function openDrawer() {
        if (bookingDrawer && drawerBackdrop) {
            drawerBackdrop.classList.remove("hidden");
            drawerBackdrop.setAttribute("aria-hidden", "false");
            bookingDrawer.classList.remove("pv-booking-drawer-closed");
            bookingDrawer.classList.add("pv-booking-drawer-open");
            bookingDrawer.setAttribute("aria-hidden", "false");
            bookingDrawer.classList.remove("translate-x-full");
        }
    }

    function closeDrawer() {
        if (bookingDrawer && drawerBackdrop) {
            bookingDrawer.classList.remove("pv-booking-drawer-open");
            bookingDrawer.classList.add("pv-booking-drawer-closed");
            bookingDrawer.setAttribute("aria-hidden", "true");
            bookingDrawer.classList.add("translate-x-full");
            setTimeout(function () {
                drawerBackdrop.classList.add("hidden");
                drawerBackdrop.setAttribute("aria-hidden", "true");
            }, 300);
        }
    }

    const mobileInfoBtn = document.getElementById("pv-mobile-info-btn");
    if (mobileInfoBtn) {
        mobileInfoBtn.addEventListener("click", openDrawer);
    }
    if (infoToggleBtn) {
        infoToggleBtn.addEventListener("click", openDrawer);
    }
    if (closeDrawerBtn) {
        closeDrawerBtn.addEventListener("click", closeDrawer);
    }
    if (drawerBackdrop) {
        drawerBackdrop.addEventListener("click", closeDrawer);
    }
});
