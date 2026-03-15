# Sample Application - To Do List
# This fixture has a bug that needs to be found and fixed

class TodoList:
    def __init__(self):
        self.items = []
        self.next_id = 1
    
    def add(self, title, description=""):
        item = {
            "id": self.next_id,
            "title": title,
            "description": description,
            "completed": False
        }
        self.items.append(item)
        self.next_id += 1
        return item
    
    def complete(self, item_id):
        for item in self.items:
            if item["id"] == item_id:
                item["completed"] = True
                return True
        return False
    
    def get_all(self):
        return self.items
    
    def get_active(self):
        return [i for i in self.items if not i["completed"]]


# BUG: This function is broken - it returns completed items instead of active
def get_pending_items(todo_list):
    """Get all pending (non-completed) items"""
    # BUG: Wrong logic - returns completed items
    return [i for i in todo_list.get_all() if i["completed"]]


# Test with bug
if __name__ == "__main__":
    todo = TodoList()
    todo.add("Buy groceries")
    todo.add("Walk the dog")
    todo.add("Finish project")
    
    # Mark one as complete
    todo.complete(1)
    
    # This should return items 2 and 3, but returns item 1 due to bug
    pending = get_pending_items(todo)
    print("Pending items:", pending)
