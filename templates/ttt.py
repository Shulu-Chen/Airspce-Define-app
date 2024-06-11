import gurobipy as gp
from gurobipy import GRB

# Sample data
Z = 100  # total number of passengers
S = 4  # number of seats per aircraft
G = [8, 8, 8, 8]  # maximum number of gates per vertiport
A = 10  # fixed number of aircraft
passenger_data = [
    (0, 1, 2, 10),  # (passenger_id, origin_vertiport, destination_vertiport, arrival_time)
    (1, 2, 3, 20),
    (2, 3, 4, 20),
    (3, 3, 4, 20),
    (4, 3, 4, 20),
    (5, 3, 4, 20),
    (6, 3, 4, 21)
]
vertiports = [1, 2, 3, 4]
time_intervals = list(range(24))  # example: 24 hourly intervals
flying_time = {(1, 2): 1, (2, 3): 1, (3, 4): 1, (4, 1): 1}  # flying times between vertiports
charging_time = 1  # charging time of aircraft

# Create a model
model = gp.Model('air_taxi_optimization')

# Decision variables
x = model.addVars(vertiports, vertiports, range(A), time_intervals, vtype=GRB.BINARY, name='x')
z = model.addVars(len(passenger_data), vtype=GRB.BINARY, name='z')
y = model.addVars(vertiports, time_intervals, vtype=GRB.INTEGER, name='y')
p = model.addVars(vertiports, range(A), time_intervals, vtype=GRB.BINARY, name='p')

# Objective function: Maximize the number of passengers served
model.setObjective(gp.quicksum(z[s] for s in range(len(passenger_data))), GRB.MAXIMIZE)

# Constraints

# Gates constraint at each vertiport
for i in vertiports:
    for t in time_intervals:
        model.addConstr(y[i, t] <= G[i - 1])

# Aircraft presence at vertiports over time
for i in vertiports:
    for t in range(len(time_intervals) - 1):
        arrivals = gp.quicksum(x[j, i, k, t - flying_time.get((j, i), 0)]
                               for j in vertiports for k in range(A)
                               if (j != i) and (t - flying_time.get((j, i), 0) >= 0))
        departures = gp.quicksum(x[i, j, k, t] for j in vertiports for k in range(A) if j != i)
        model.addConstr(y[i, t + 1] == y[i, t] + arrivals - departures)

# Initial number of aircraft can be distributed among all vertiports
model.addConstr(gp.quicksum(y[i, 0] for i in vertiports) == A)

# Passenger capacity constraint for each flight
for i in vertiports:
    for j in vertiports:
        if i != j:
            for k in range(A):
                for t in time_intervals:
                    model.addConstr(gp.quicksum(z[p] for p, (pid, o_p, d_p, t_p) in enumerate(passenger_data) if o_p == i and d_p == j and t_p == t) <= S)

# Passenger timing constraint
for s, (pid, o_p, d_p, t_p) in enumerate(passenger_data):
    model.addConstr(z[s] <= gp.quicksum(x[o_p, d_p, k, t] for k in range(A) for t in time_intervals if t_p - 0.5 <= t <= t_p + 0.5))

# Flight scheduling constraint considering flying and charging times
for i in vertiports:
    for j in vertiports:
        for k in range(A):
            for t in time_intervals:
                if t + flying_time.get((i, j), 0) + charging_time < len(time_intervals):
                    model.addConstr(x[i, j, k, t] + x[j, i, k, t + flying_time.get((i, j), 0) + charging_time] <= 1)

# Ensure aircraft that arrive must depart or park
for i in vertiports:
    for k in range(A):
        for t in range(len(time_intervals) - 1):
            arrivals = gp.quicksum(x[j, i, k, t - flying_time.get((j, i), 0)]
                                   for j in vertiports if (j != i) and (t - flying_time.get((j, i), 0) >= 0))
            departures = gp.quicksum(x[i, j, k, t] for j in vertiports if j != i)
            model.addConstr(p[i, k, t + 1] == p[i, k, t] + arrivals - departures)

# Prevent scheduling flights with the same origin and destination vertiport
for i in vertiports:
    for k in range(A):
        for t in time_intervals:
            model.addConstr(x[i, i, k, t] == 0)

# Optimize the model
model.optimize()

# Print the results
if model.status == GRB.OPTIMAL:
    print(f'Optimal number of passengers served: {model.objVal}')
    for p in range(len(passenger_data)):
        if z[p].X > 0.5:
            print(f'Passenger {p+1} is served')
    for i in vertiports:
        for j in vertiports:
            for k in range(A):
                for t in time_intervals:
                    if x[i, j, k, t].X > 0.5:
                        print(f'Flight from vertiport {i} to vertiport {j} at time {t} with aircraft {k+1}')
else:
    print('No optimal solution found.')
