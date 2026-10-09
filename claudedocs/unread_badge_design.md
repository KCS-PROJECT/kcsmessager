# Unread Message Badge Design Specification
## KCS Messenger - Friends Tab Enhancement

**Version**: 1.0
**Date**: 2025-10-16
**Status**: Design Complete - Ready for Implementation

---

## 1. Executive Summary

This document specifies the design for adding unread message badges to the Friends Tab in KCS Messenger. When a user receives messages from a friend, a red circular badge with the message count will appear next to their name in the friends list, following KakaoTalk's visual design patterns.

### Key Features
- Real-time unread message count display
- KakaoTalk-style red circular badges
- Automatic badge clearing when chat is opened
- Session-based tracking (no persistence required)
- No server-side changes needed

---

## 2. System Architecture

### 2.1 Architecture Overview

```
┌───────────────────────────────────────────────────────────┐
│                      MainWindow                            │
│                                                            │
│  ┌──────────────────────────────────────────────────┐    │
│  │  Message Receive Thread                           │    │
│  │                                                    │    │
│  │  receive_messages()                               │    │
│  │         ↓                                          │    │
│  │  handle_message()                                 │    │
│  │         ↓                                          │    │
│  │  Check: Is ChatWindow visible?                    │    │
│  │         ↓ No                    ↓ Yes             │    │
│  │  increment_unread()      Do nothing               │    │
│  └──────────────────────────────────────────────────┘    │
│                                                            │
│  ┌──────────────────────────────────────────────────┐    │
│  │  Chat Window Management                           │    │
│  │                                                    │    │
│  │  open_chat_window()                               │    │
│  │         ↓                                          │    │
│  │  clear_unread(username)                           │    │
│  │         ↓                                          │    │
│  │  Open/Show ChatWindow                             │    │
│  └──────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────┘
                          ↓
        ┌─────────────────────────────────────┐
        │         FriendsTab                   │
        │                                      │
        │  State:                              │
        │  - unread_counts: Dict[str, int]    │
        │                                      │
        │  Methods:                            │
        │  + increment_unread(username)        │
        │  + clear_unread(username)            │
        │  + get_unread_count(username)        │
        │  + refresh_user_list()               │
        └─────────────────────────────────────┘
                          ↓
    ┌────────────────────────────────────────────┐
    │      FriendListItemWidget                  │
    │                                            │
    │  Properties:                               │
    │  - username: str                           │
    │  - is_online: bool                         │
    │  - unread_count: int                       │
    │                                            │
    │  Rendering:                                │
    │  - paintEvent() → Draw badge if count > 0 │
    └────────────────────────────────────────────┘
```

### 2.2 Data Flow

#### Scenario 1: Message Received
```
1. Server broadcasts message
   ↓
2. MainWindow.receive_messages() gets data
   ↓
3. MainWindow.handle_message() parses JSON
   ↓
4. Check if ChatWindow for sender exists and is visible
   ↓
5. If NOT visible:
   - FriendsTab.increment_unread(sender)
   - FriendsTab.refresh_user_list()
   - Badge appears in UI
```

#### Scenario 2: Chat Window Opened
```
1. User double-clicks friend in list
   ↓
2. FriendsTab.chat_requested signal emitted
   ↓
3. MainWindow.open_chat_window(username)
   ↓
4. FriendsTab.clear_unread(username)
   ↓
5. FriendsTab.refresh_user_list()
   ↓
6. Badge disappears from UI
   ↓
7. ChatWindow shown to user
```

---

## 3. Component Design

### 3.1 FriendsTab Class Enhancement

#### New State Variables
```python
class FriendsTab(QWidget):
    def __init__(self, my_username, parent=None):
        # ... existing code ...
        self.unread_counts = {}  # {username: int} - tracks unread messages
```

#### New Methods

**increment_unread(username: str) -> None**
```python
def increment_unread(self, username: str) -> None:
    """
    Increment unread message count for specified user.

    Args:
        username: User who sent the message

    Side Effects:
        - Increments count in unread_counts dictionary
        - Triggers UI refresh via refresh_user_list()
    """
    current_count = self.unread_counts.get(username, 0)
    self.unread_counts[username] = current_count + 1
    self.refresh_user_list()
```

**clear_unread(username: str) -> None**
```python
def clear_unread(self, username: str) -> None:
    """
    Clear unread message count for specified user.

    Args:
        username: User whose messages were read

    Side Effects:
        - Removes entry from unread_counts dictionary
        - Triggers UI refresh via refresh_user_list()
    """
    if username in self.unread_counts:
        del self.unread_counts[username]
        self.refresh_user_list()
```

**get_unread_count(username: str) -> int**
```python
def get_unread_count(self, username: str) -> int:
    """
    Get current unread count for user.

    Args:
        username: User to check

    Returns:
        Unread message count (0 if no unread messages)
    """
    return self.unread_counts.get(username, 0)
```

#### Modified Methods

**refresh_user_list() - Enhancement**
```python
def refresh_user_list(self):
    """
    Refresh user list UI with online status and unread badges.

    Changes from original:
        - Uses custom FriendListItemWidget instead of QListWidgetItem
        - Passes unread_count to widget constructor
        - Widget handles badge rendering
    """
    self.user_list.clear()

    # ... existing sorting logic ...

    for user in online_list:
        unread_count = self.get_unread_count(user)

        # Create custom widget with badge support
        widget = FriendListItemWidget(
            username=user,
            is_online=True,
            unread_count=unread_count
        )

        item = QListWidgetItem()
        item.setData(Qt.UserRole, user)
        item.setSizeHint(widget.sizeHint())

        self.user_list.addItem(item)
        self.user_list.setItemWidget(item, widget)
```

### 3.2 FriendListItemWidget Class (New)

#### Class Definition
```python
class FriendListItemWidget(QWidget):
    """
    Custom widget for friend list items with unread badge support.

    Displays:
    - Online/offline status indicator (●/○)
    - Username
    - Unread message badge (if count > 0)
    """

    def __init__(self, username: str, is_online: bool, unread_count: int, parent=None):
        super().__init__(parent)
        self.username = username
        self.is_online = is_online
        self.unread_count = unread_count

        self.setFixedHeight(50)
        self.setAttribute(Qt.WA_StyledBackground, True)
```

#### Methods

**sizeHint() -> QSize**
```python
def sizeHint(self):
    """Return preferred size for layout."""
    return QSize(400, 50)
```

**set_unread_count(count: int) -> None**
```python
def set_unread_count(self, count: int):
    """
    Update unread count and trigger repaint.

    Args:
        count: New unread message count
    """
    self.unread_count = count
    self.update()  # Trigger repaint
```

**paintEvent(event: QPaintEvent) -> None**
```python
def paintEvent(self, event):
    """
    Custom paint event to draw status indicator, username, and badge.

    Layout:
    [10px] ● [8px] Username                    Badge [10px]

    Components:
    1. Status Indicator: Filled (●) or hollow (○) circle
    2. Username: Left-aligned text
    3. Badge: Right-aligned circular badge with count
    """
    painter = QPainter(self)
    painter.setRenderHint(QPainter.Antialiasing)

    # 1. Draw status indicator
    x = 15
    y = 25
    status_color = QColor(0, 150, 0) if self.is_online else QColor(150, 150, 150)

    painter.setPen(QPen(status_color, 2))
    if self.is_online:
        painter.setBrush(QBrush(status_color))
        painter.drawEllipse(x, y-4, 8, 8)
    else:
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(x, y-4, 8, 8)

    # 2. Draw username
    painter.setFont(QFont('맑은 고딕', 14))
    text_color = QColor(0, 0, 0) if self.is_online else QColor(150, 150, 150)
    painter.setPen(text_color)
    painter.drawText(x + 16, y + 5, self.username)

    # 3. Draw badge (if unread_count > 0)
    if self.unread_count > 0:
        # Badge text
        badge_text = str(self.unread_count) if self.unread_count <= 99 else "99+"

        # Calculate badge dimensions
        badge_font = QFont('맑은 고딕', 11, QFont.Bold)
        fm = painter.fontMetrics()
        text_width = fm.horizontalAdvance(badge_text)
        badge_width = max(20, text_width + 12)
        badge_height = 20

        # Badge position (right edge)
        badge_x = self.width() - badge_width - 10
        badge_y = (self.height() - badge_height) // 2

        # Draw badge background
        painter.setBrush(QBrush(QColor(255, 59, 48)))  # KakaoTalk red
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(badge_x, badge_y, badge_width, badge_height,
                               badge_height // 2, badge_height // 2)

        # Draw badge text
        painter.setFont(badge_font)
        painter.setPen(QColor(255, 255, 255))  # White text
        text_rect = QRect(badge_x, badge_y, badge_width, badge_height)
        painter.drawText(text_rect, Qt.AlignCenter, badge_text)
```

### 3.3 MainWindow Class Enhancement

#### Modified Methods

**handle_message(data: str) -> None**
```python
def handle_message(self, data):
    """
    Handle incoming messages from server.

    Enhancement:
        - Check if ChatWindow is visible before incrementing unread
        - Increment unread count for background/hidden chats
    """
    try:
        msg = json.loads(data)
        msg_type = msg.get('type')

        # ... existing code for all_users_list, user_status_changed ...

        elif msg_type == 'message':
            sender = msg.get('sender')
            content = msg.get('content')
            timestamp = msg.get('timestamp', datetime.now().strftime('%H:%M'))

            if sender == self.username:
                return  # Ignore own messages

            # === NEW LOGIC: Check visibility ===
            chat_window_visible = (
                sender in self.chat_windows and
                self.chat_windows[sender].isVisible()
            )

            if not chat_window_visible:
                # Increment unread count if window not visible
                self.friends_tab.increment_unread(sender)

            # Update chat list
            self.chats_tab.add_or_update_chat(sender, content, datetime.now())

            # Add message to window if exists
            if sender in self.chat_windows:
                chat_window = self.chat_windows[sender]
                chat_window.add_message(sender, content, timestamp, is_mine=False)

    except json.JSONDecodeError as e:
        print(f"JSON 파싱 오류: {e}")
```

**open_chat_window(target_user: str) -> None**
```python
def open_chat_window(self, target_user):
    """
    Open or show chat window for target user.

    Enhancement:
        - Clear unread count when opening chat
    """
    # === NEW LOGIC: Clear unread count ===
    self.friends_tab.clear_unread(target_user)

    if target_user in self.chat_windows:
        # Show existing window
        chat_window = self.chat_windows[target_user]
        chat_window.show()
        chat_window.activateWindow()
    else:
        # Create new window
        chat_window = ChatWindow(target_user, self.username)
        chat_window.message_sent.connect(self.send_message)
        self.chat_windows[target_user] = chat_window
        chat_window.show()
```

### 3.4 ChatWindow Class Enhancement (Optional)

#### Additional Enhancement for Window Restoration
```python
def showEvent(self, event):
    """
    Handle window show event to clear unread count.

    This catches cases where window is restored from minimized state.
    """
    super().showEvent(event)
    # Could emit signal to clear unread, but open_chat_window already handles this
```

---

## 4. Visual Design Specification

### 4.1 Badge Design

#### Visual Properties
```yaml
Badge Appearance:
  Shape: Perfect circle or rounded rectangle
  Background: '#FF3B30' (iOS/KakaoTalk red)
  Text Color: '#FFFFFF' (white)
  Font: '맑은 고딕', 11px, bold

Dimensions:
  Min Width: 20px
  Min Height: 20px
  Padding: 3px 6px (horizontal)
  Border Radius: 10px (half of height)

Position:
  Alignment: Right edge of list item
  Margin Right: 10px
  Vertical: Centered in 50px item height

Text Content:
  Display: Numeric count
  Max Display: "99+" for counts > 99
  Alignment: Center
```

#### Color Palette
```
Primary Badge Red:   #FF3B30  (RGB: 255, 59, 48)
Badge Text White:    #FFFFFF  (RGB: 255, 255, 255)
Online Green:        #009600  (RGB: 0, 150, 0)
Offline Gray:        #969696  (RGB: 150, 150, 150)
Background White:    #FFFFFF  (RGB: 255, 255, 255)
Hover Background:    #F5F5F5  (RGB: 245, 245, 245)
```

### 4.2 List Item Layout

```
┌────────────────────────────────────────────────────┐
│                                                    │
│  [10px] ● [8px] 홍길동                        ⊕ 3  │  ← 50px height
│                                              [10px]│
│                                                    │
└────────────────────────────────────────────────────┘
        ↑         ↑                             ↑
    Status    Username                       Badge
  Indicator   (14px)                         (20px)
```

**Layout Breakdown:**
- **Left Margin**: 10px
- **Status Indicator**: 8px circle (●/○)
- **Spacing**: 8px
- **Username**: Left-aligned, flexible width
- **Stretch**: Fills remaining space
- **Badge**: Right-aligned, 20px min width
- **Right Margin**: 10px

### 4.3 Interactive States

**Normal State**
- Background: White (#FFFFFF)
- Text: Black (#000000) for online, Gray (#969696) for offline

**Hover State**
- Background: Light Gray (#F5F5F5)
- Text: Same as normal
- Badge: No change

**Selected State** (if implemented)
- Background: Light Blue (#E3F2FD)
- Text: Same as normal
- Badge: No change

---

## 5. Implementation Strategy

### 5.1 Implementation Phases

#### Phase 1: Data Layer (2-3 hours)
**Goal**: Implement unread count tracking logic

**Tasks**:
1. Add `unread_counts` dictionary to FriendsTab.__init__()
2. Implement `increment_unread()` method
3. Implement `clear_unread()` method
4. Implement `get_unread_count()` method
5. Update MainWindow.handle_message() to increment count
6. Update MainWindow.open_chat_window() to clear count

**Testing**:
- Print statements to verify counts increment/clear correctly
- Test with multiple users sending messages
- Test window open/close cycles

#### Phase 2: UI Layer (3-4 hours)
**Goal**: Implement badge visual rendering

**Tasks**:
1. Create FriendListItemWidget class
2. Implement __init__() with properties
3. Implement sizeHint() method
4. Implement paintEvent() for custom drawing:
   - Status indicator drawing
   - Username text rendering
   - Badge circle and text rendering
5. Update FriendsTab.refresh_user_list() to use custom widget
6. Handle "99+" display for counts > 99

**Testing**:
- Visual inspection of badge rendering
- Test with various unread counts (1, 10, 99, 100+)
- Test online/offline status display
- Test badge positioning at different window sizes

#### Phase 3: Integration & Polish (1-2 hours)
**Goal**: Complete integration and handle edge cases

**Tasks**:
1. Test complete message flow end-to-end
2. Handle window visibility edge cases:
   - Minimized windows
   - Hidden windows
   - Multiple windows open
3. Test with multiple simultaneous unread users
4. Performance testing with rapid messages
5. Visual polish and styling adjustments

**Testing**:
- Complete user scenario testing
- Multiple users sending messages simultaneously
- Rapid message testing
- Window state transitions

### 5.2 File Changes

**Single File Modified:**
- `/Users/joogik/develop/kcsmessager/client/realtime/chat_client_tabbed.py`

**Change Summary:**
```python
# New class added (after BubbleWithTail, before ChatWindow)
class FriendListItemWidget(QWidget):
    # ~100 lines of code

# FriendsTab class modified
class FriendsTab(QWidget):
    # Add unread_counts in __init__
    # Add 3 new methods: increment_unread, clear_unread, get_unread_count
    # Modify refresh_user_list() to use custom widget

# MainWindow class modified
class MainWindow(QMainWindow):
    # Modify handle_message() - add visibility check
    # Modify open_chat_window() - add clear_unread() call
```

**Estimated Lines of Code:**
- New code: ~150 lines
- Modified code: ~30 lines
- Total impact: ~180 lines

---

## 6. Testing Requirements

### 6.1 Functional Testing

#### Test Case 1: Badge Appears on Message Receipt
**Preconditions:**
- User A logged in
- User B logged in
- No chat windows open

**Steps:**
1. User B sends message to User A
2. Observe User A's friends list

**Expected Result:**
- Badge appears next to User B's name
- Badge shows "1"

#### Test Case 2: Badge Count Increments
**Preconditions:**
- User A has badge showing "1" for User B

**Steps:**
1. User B sends 2 more messages to User A
2. Observe User A's friends list

**Expected Result:**
- Badge updates to show "3"

#### Test Case 3: Badge Clears on Chat Open
**Preconditions:**
- User A has badge showing "3" for User B

**Steps:**
1. User A double-clicks User B in friends list
2. Observe User A's friends list

**Expected Result:**
- Badge disappears immediately
- Chat window opens with all 3 messages visible

#### Test Case 4: Badge Handles 99+ Display
**Preconditions:**
- User A not viewing User B's chat

**Steps:**
1. Send 100 messages from User B to User A
2. Observe User A's friends list

**Expected Result:**
- Badge shows "99+" instead of "100"

#### Test Case 5: Multiple Badges Simultaneously
**Preconditions:**
- User A logged in
- Users B, C, D logged in

**Steps:**
1. User B sends 2 messages to User A
2. User C sends 1 message to User A
3. User D sends 5 messages to User A
4. Observe User A's friends list

**Expected Result:**
- Badge "2" appears next to User B
- Badge "1" appears next to User C
- Badge "5" appears next to User D
- All badges visible simultaneously

### 6.2 Edge Case Testing

#### Test Case 6: Window Minimized
**Preconditions:**
- User A has chat window open with User B
- Chat window is minimized

**Steps:**
1. User B sends message
2. Observe User A's friends list

**Expected Result:**
- Badge appears (window is not visible, so count increments)

#### Test Case 7: Window Hidden
**Preconditions:**
- User A has chat window open with User B
- Chat window is hidden (not closed)

**Steps:**
1. User B sends message
2. User A clicks User B in friends list
3. Observe badge and window

**Expected Result:**
- Badge clears
- Existing window shows up (not created new)

#### Test Case 8: Rapid Messages
**Preconditions:**
- User A logged in

**Steps:**
1. User B sends 10 messages rapidly (< 1 second)
2. Observe User A's friends list

**Expected Result:**
- Badge shows "10"
- No duplicate badges
- No UI lag or freeze

### 6.3 Visual Testing

#### Test Case 9: Badge Styling
**Steps:**
1. Create badge with count = 5
2. Inspect visual appearance

**Expected Result:**
- Circular/rounded rectangle shape
- Red background (#FF3B30)
- White text (#FFFFFF)
- Text centered in badge
- Badge positioned at right edge

#### Test Case 10: Responsive Layout
**Steps:**
1. Resize main window to various widths (400px - 800px)
2. Observe badge positioning

**Expected Result:**
- Badge remains at right edge with 10px margin
- Badge does not overlap username
- Layout remains stable

### 6.4 Performance Testing

#### Test Case 11: Many Unread Users
**Steps:**
1. Have 10 users send messages to User A
2. Each user sends 5 messages
3. Observe UI responsiveness

**Expected Result:**
- All 10 badges display correctly
- No UI lag when scrolling friends list
- Refresh_user_list() completes quickly (<100ms)

---

## 7. Future Enhancements

### 7.1 Potential Improvements (Not in Current Scope)

**Badge Animations**
- Fade in/out when appearing/disappearing
- Pulse animation for new messages
- Smooth count transitions

**Persistence**
- Save unread counts to local storage
- Restore counts on application restart
- Sync counts across devices (requires server support)

**Advanced Features**
- Separate read/delivered/sent status
- Per-message read receipts
- Group chat badge support
- Notification integration

**Settings**
- User preference to disable badges
- Custom badge colors
- Badge position customization

### 7.2 Known Limitations

**Session-Based Tracking**
- Unread counts reset on application restart
- No persistence between sessions
- No cross-device synchronization

**Window Visibility Detection**
- Does not detect if window is on another desktop/workspace
- Does not detect if window is covered by other windows
- Simple isVisible() check only

**No Server-Side Tracking**
- Server does not track read/unread status
- Cannot sync read status across multiple clients
- No read receipt confirmation to sender

---

## 8. Success Criteria

### 8.1 Functional Criteria
✅ Badge appears when message received and chat not visible
✅ Badge count increments correctly for multiple messages
✅ Badge clears immediately when chat window opened
✅ Badge displays "99+" for counts over 99
✅ Multiple badges can appear simultaneously
✅ Badge state updates in real-time

### 8.2 Visual Criteria
✅ Badge matches KakaoTalk visual style
✅ Badge positioned correctly at right edge
✅ Badge readable with high contrast
✅ Badge scales correctly at different DPI settings
✅ No visual glitches or flickering
✅ Smooth UI updates without lag

### 8.3 Performance Criteria
✅ Badge updates complete in < 50ms
✅ No UI lag with multiple badges
✅ Efficient memory usage (minimal overhead)
✅ No performance degradation over time

---

## 9. Conclusion

This design specification provides a complete blueprint for implementing unread message badges in the KCS Messenger friends tab. The solution is:

- **Self-Contained**: All changes in single client file
- **Simple**: No server modifications required
- **Performant**: Minimal computational overhead
- **Maintainable**: Clear separation of concerns
- **Scalable**: Handles multiple simultaneous unread users
- **User-Friendly**: Follows familiar KakaoTalk patterns

The implementation is estimated at 6-9 hours of development time and follows a phased approach that allows for incremental testing and validation.

---

## Appendices

### Appendix A: Code Snippets

See Section 3 (Component Design) for detailed code specifications.

### Appendix B: Visual Mockups

```
Before:
┌────────────────────────────┐
│ ● 홍길동                    │
│ ● 김철수                    │
│ ○ 이영희                    │
└────────────────────────────┘

After (with unread messages):
┌────────────────────────────┐
│ ● 홍길동              ⊕ 3  │  ← Badge shows 3 unread
│ ● 김철수              ⊕ 1  │  ← Badge shows 1 unread
│ ○ 이영희                    │  ← No unread messages
└────────────────────────────┘
```

### Appendix C: Color Reference

```css
/* Badge Colors */
--badge-red: #FF3B30;
--badge-text: #FFFFFF;

/* Status Colors */
--online-green: #009600;
--offline-gray: #969696;

/* Background Colors */
--bg-white: #FFFFFF;
--bg-hover: #F5F5F5;

/* Text Colors */
--text-black: #000000;
--text-gray: #969696;
```

---

**Document End**
