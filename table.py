import random

BUSES = 8
WORK_DAYS = 5
REST_DAYS = 2
FULL_TIME = 96
DAY_NAMES = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
POPULATION_SIZE = 50
GENERATIONS = 20
MUTATION = 0.01

# Перевод числа в строку времени
def int2time(num: int):
    num %= FULL_TIME
    return ("0" + str(num//4) if num//4 < 10 else str(num//4)) + ":" + ("0" + str((num%4)*15) if (num%4)*15 < 10 else str((num%4)*15))

class Driver:
    def __init__(self, id: int, shift_type: int):
        self.id = id
        self.shift_type = shift_type # -1 - 8 часов; 0-2 - 12 часов
        self.table = [None for j in range(WORK_DAYS + REST_DAYS)] # Массив для вывода расписания
    # Перевод класса в строку выводит расписание водителя 
    def __str__(self): 
        output_table = "Водитель " + str(self.id) + " (смена " + ("12" if (self.shift_type >= 0) else "8") + " часов):\n"
        for i in range(len(self.table)):
            if self.table[i]:
                output_table += "\t" + DAY_NAMES[i] + " - " + int2time(self.table[i]["time"][0]) + "-" + int2time(self.table[i]["time"][1])
                output_table += " - Автобус №" + str(self.table[i]["bus"]) + "\n\tПерерывы:\n"
                for time_break in self.table[i]["breaks"]:
                    output_table += "\t\t" + int2time(time_break[0]) + "-" + int2time(time_break[1]) + "\n"
        return output_table[0:-1]

class Bus:
    def __init__(self, id):
        self.id = id
        self.table = [[] for j in range(WORK_DAYS + REST_DAYS)] # Массив поиска свободных автобусов
        self.tmp_table = [[] for j in range(WORK_DAYS + REST_DAYS)] # Массив для генетического алгоритма

# В автобусе фиксированное кол-во автобусов
buses = [Bus(i) for i in range(BUSES)]
base_drivers = []

def get_free_bus(day: int, new_start: int, new_end):
    for bus in buses:
        # Проверка на использование автобуса сегодня, вчера и завтра
        free_now = True
        free_in_past = True
        free_in_next = True
        for timestamp in (bus.table[day] + bus.tmp_table[day]):
            free_now = (new_end < timestamp["time"][0]) or (new_start > timestamp["time"][1])
            if not free_now:
                break
        if day > 0:
            for timestamp in (bus.table[day-1] + bus.tmp_table[day-1]):
                free_in_past = (timestamp["time"][1] < FULL_TIME) or (new_start+FULL_TIME > timestamp["time"][1])
                if not free_in_past:
                    break
        if day < WORK_DAYS+REST_DAYS-1:
            for timestamp in (bus.table[day+1] + bus.tmp_table[day+1]):
                if ((new_end > FULL_TIME) and (new_end > timestamp["time"][0]+FULL_TIME)):
                    free_in_past = False
                    break
        if free_now and free_in_past and free_in_next:
            return bus
    return None

def get_free_driver(drivers, day: int):
    for driver in drivers:
        if (driver.shift_type < 0 or driver.shift_type == day%3) and not driver.table[day]:
            return driver
    return None

# Инициализация начальных водителей 12-часовой смены
for day in range(WORK_DAYS + REST_DAYS):
    for i in range(4):
        start = (i%4)*22
        end = start+48
        free_driver = get_free_driver(base_drivers, day)
        if not free_driver: # если нет свободного водителя, создать нового
            base_drivers.append(Driver(len(base_drivers), day%3))
            free_driver = base_drivers[-1]
        free_bus = get_free_bus(day, start, end)
        free_driver.table[day] = {"time": (start, end), "breaks": [((start-1+j*8)%FULL_TIME, (start+j*8)%FULL_TIME) for j in range(1, 6)], "bus": free_bus.id}
        free_bus.table[day].append({"time": (start, end), "driver": free_driver.id})

# Генерация новых водителей
def generate_population(attempts: int):
    new_drivers = []
    for day in range(WORK_DAYS + REST_DAYS):
        for i in range(attempts):
            is8hr = bool(random.randint(0, 1))
            start = random.randint(24, 40) if is8hr else random.randint(0, 95)
            end = start+(32 if is8hr else 48)
            free_driver = get_free_driver(base_drivers + new_drivers, day)
            if not free_driver:
                free_driver = Driver(len(base_drivers + new_drivers), (-1 if is8hr else day%3))
            free_bus = get_free_bus(day, start, end)
            if free_bus:
                breaks = []
                if is8hr:
                    for lunch in range(start, end, 7):
                        if lunch > 52:
                            breaks = [(lunch, lunch+4)]
                            break
                else:
                    breaks = [((start-1+j*8)%FULL_TIME, (start+j*8)%FULL_TIME) for j in range(1, 6)]
                free_driver.table[day] = {"time": (start, end), "breaks": breaks, "bus": free_bus.id}
                free_bus.tmp_table[day].append({"time": (start, end), "driver": free_driver.id})
                if not (free_driver in new_drivers):
                    new_drivers.append(free_driver)
    for bus in buses:
        bus.tmp_table = [[] for j in range(WORK_DAYS + REST_DAYS)]
    return new_drivers

def fintess_function(population):
    score = 0
    for driver in population:
        score += 4 if (driver.shift_type < 0) else 7
    return score

def selection(population, fitness_scores):
    try:
        return random.choices(population, weights=[max(fitness_scores) - score for score in fitness_scores], k=2)
    except:
        return random.choices(population, k=2)

def crossover(parent1, parent2):
    point = random.randint(1, len(parent1) - 1)
    return parent1[:point] + parent2[point:], parent2[:point] + parent1[point:]

def mutation_fit(schedule, driver: Driver, day: int, start: int, end: int):
    for others in schedule:
        if driver != others:
            if others.table[day] and (driver.table[day]["bus"] == others.table[day]["bus"]):
                if (end > others.table[day]["time"][0] and start < others.table[day]["time"][1]) or (end < others.table[day]["time"][0] and start > others.table[day]["time"][1]):
                    return False
            if day > 0 and others.table[day-1] and (driver.table[day]["bus"] == others.table[day-1]["bus"]):
                if (others.table[day-1]["time"][1] < FULL_TIME) or (start+FULL_TIME > others.table[day-1]["time"][1]):
                    return False
            if day < WORK_DAYS+REST_DAYS-1 and others.table[day+1] and (driver.table[day]["bus"] == others.table[day+1]["bus"]):
                if (end > FULL_TIME and end > others.table[day+1]["time"][0]+FULL_TIME):
                    return False
    return True

def mutation(schedule):
    for i in range(len(schedule)):
        for day in range(len(schedule[i].table)):
            if random.random() < MUTATION and schedule[i].table[day]:
                start = random.randint(24, 40) if (schedule[i].shift_type < 0) else random.randint(0, 95)
                end = start+(32 if (schedule[i].shift_type < 0) else 48)
                if mutation_fit(schedule, schedule[i], day, start, end):
                    schedule[i].table[day]["time"] = (start, end)

    return schedule

def genetic_alg(generations: int):
    generation = []
    for i in range(POPULATION_SIZE):
        generation.append(generate_population(10))
    for i in range(generations):
        fitness_scores = [fintess_function(schedule) for schedule in generation]

        new_generation = []
        for j in range(len(generation)//2):
            best1, best2 = selection(generation, fitness_scores)
            new_schedule1, new_schedule2 = crossover(best1, best2)
            new_generation += [mutation(new_schedule1), mutation(new_schedule2)]
        generation = new_generation
    best_schedule = max(generation, key=fintess_function)
    return best_schedule

generated_drivers = genetic_alg(GENERATIONS)

def get_day_table(drivers, day: int):
    output = "Расписание выезда автобусов на " + DAY_NAMES[day] + ":\n"
    for driver in drivers:
        if driver.table[day]:
            output += "\tВодитель " + str(driver.id) + " - "
            output += int2time(driver.table[day]["time"][0]) + "-" + int2time(driver.table[day]["time"][1])
            output += " - Автобус №" + str(driver.table[day]["bus"]) + "\n"
    return output[0:-1]

for i in range(WORK_DAYS + REST_DAYS):
    print(get_day_table(base_drivers + generated_drivers, i))
print("Всего водителей: " + str(len(base_drivers+generated_drivers)))
