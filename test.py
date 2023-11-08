import schedule
import time

def job():
    print("I'm working...")

schedule.every(10).seconds.do(job)

if __name__ == '__main__':
    job()
    while True:
        schedule.run_pending()
        time.sleep(1)
