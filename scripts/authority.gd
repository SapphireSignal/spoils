extends Node
## Authority: every authoritative game-state mutation routes through this
## autoload (spawns now; damage/loot/extraction in later milestones). This is
## the seam a future multiplayer server would own — gameplay code must call
## these functions instead of mutating state directly.


func spawn_player(parent: Node, pos: Vector2) -> Player:
	var player := Player.new()
	player.name = "Player"
	player.position = pos
	parent.add_child(player)
	player.reset_physics_interpolation()  # no first-frame streak from (0,0)
	return player
