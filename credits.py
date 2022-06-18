class Credits:
    credits = 0

    def __init__(self,num):
        self.credits = num

    def get_credits(self):
        return self.credits

    def set_credits(self,num):
        self.credits = num
    
    def increment(self):
        self.credits += 1

    def decrement(self):
        self.credits -= 1
