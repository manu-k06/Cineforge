/**
 * Cineforge Superhero Avatar Registry
 * High-definition hero emblems extracted for user profiles
 */

export const SUPERHERO_AVATARS = [
  { id: 'spider_man', name: 'Spider-Man', src: '/assets/images/avatars/spider_man.png', color: '#E50914' },
  { id: 'iron_man', name: 'Iron Man', src: '/assets/images/avatars/iron_man.png', color: '#FBBF24' },
  { id: 'captain_america', name: 'Captain America', src: '/assets/images/avatars/captain_america.png', color: '#3B82F6' },
  { id: 'deadpool', name: 'Deadpool', src: '/assets/images/avatars/deadpool.png', color: '#DC2626' },
  { id: 'black_panther', name: 'Black Panther', src: '/assets/images/avatars/black_panther.png', color: '#8B5CF6' },
  { id: 'thor', name: 'Thor', src: '/assets/images/avatars/thor.png', color: '#60A5FA' },
  { id: 'doctor_strange', name: 'Doctor Strange', src: '/assets/images/avatars/doctor_strange.png', color: '#06B6D4' },
  { id: 'miles_morales', name: 'Miles Morales', src: '/assets/images/avatars/miles_morales.png', color: '#EF4444' },
  { id: 'loki', name: 'Loki', src: '/assets/images/avatars/loki.png', color: '#10B981' },
  { id: 'hulk', name: 'Hulk', src: '/assets/images/avatars/hulk.png', color: '#22C55E' },
  { id: 'x_men', name: 'X-Men', src: '/assets/images/avatars/x_men.png', color: '#EAB308' },
  { id: 'avengers', name: 'Avengers', src: '/assets/images/avatars/avengers.png', color: '#3B82F6' },
  { id: 'scarlet_witch', name: 'Scarlet Witch', src: '/assets/images/avatars/scarlet_witch.png', color: '#EC4899' },
  { id: 'black_widow', name: 'Black Widow', src: '/assets/images/avatars/black_widow.png', color: '#EF4444' },
  { id: 'captain_marvel', name: 'Captain Marvel', src: '/assets/images/avatars/captain_marvel.png', color: '#F59E0B' },
  { id: 'ant_man', name: 'Ant-Man', src: '/assets/images/avatars/ant_man.png', color: '#EF4444' },
  { id: 'wasp', name: 'Wasp', src: '/assets/images/avatars/wasp.png', color: '#FBBF24' },
  { id: 'falcon', name: 'Falcon', src: '/assets/images/avatars/falcon.png', color: '#EF4444' },
  { id: 'shield', name: 'S.H.I.E.L.D.', src: '/assets/images/avatars/shield.png', color: '#3B82F6' },
  { id: 'arc_reactor', name: 'Arc Reactor', src: '/assets/images/avatars/arc_reactor.png', color: '#38BDF8' },
  { id: 'hawkeye', name: 'Hawkeye', src: '/assets/images/avatars/hawkeye.png', color: '#A855F7' },
  { id: 'fantastic_four', name: 'Fantastic Four', src: '/assets/images/avatars/fantastic_four.png', color: '#38BDF8' },
  { id: 'storm', name: 'Storm', src: '/assets/images/avatars/storm.png', color: '#67E8F9' },
  { id: 'shang_chi', name: 'Shang-Chi', src: '/assets/images/avatars/shang_chi.png', color: '#F59E0B' },
]

export const DEFAULT_AVATAR = SUPERHERO_AVATARS[0] // Spider-Man

/**
 * Returns the avatar image source URL for a given avatar identifier
 */
export function getAvatarSrc(avatarId) {
  if (!avatarId) return DEFAULT_AVATAR.src
  const match = SUPERHERO_AVATARS.find((a) => a.id === avatarId)
  return match ? match.src : DEFAULT_AVATAR.src
}

/**
 * Returns full avatar info object by ID
 */
export function getAvatarInfo(avatarId) {
  if (!avatarId) return DEFAULT_AVATAR
  const match = SUPERHERO_AVATARS.find((a) => a.id === avatarId)
  return match || DEFAULT_AVATAR
}
