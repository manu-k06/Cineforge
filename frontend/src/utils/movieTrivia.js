/**
 * Cineforge Pre-Show Movie Trivia Engine
 * Supplies captivating behind-the-scenes facts, director secrets, and easter eggs.
 */

const CURATED_TRIVIA = {
  spider_man: [
    "Over 1,000 animators worked on Across the Spider-Verse, making it the largest crew ever assembled for an animated feature film. Each dimension features its own distinct art style.",
    "The iconic 'Spider-Man Pointing' meme was re-enacted live by Tobey Maguire, Andrew Garfield, and Tom Holland during their top-secret joint photoshoot.",
    "Miles Morales' sneakers in Into the Spider-Verse are authentic Air Jordan 1s. Nike actually produced a limited retail run called the 'Origin Story' to commemorate the film.",
  ],
  dune: [
    "Denis Villeneuve avoided using green or blue screens for Arrakis, opting instead for 'sandscreens'—giant fabric backdrops colored like the desert so ambient reflections on actors' skin were 100% natural.",
    "Sound designer Mark Mangini recorded the sound of sandworms moving beneath the sand by placing hydrophones inside desert dunes while desert beetles burrowed nearby.",
    "Hans Zimmer spent months crafting entirely fictional instruments and alien vocal scales because he felt standard orchestra instruments wouldn't fit a story set 20,000 years in the future.",
  ],
  interstellar: [
    "The theoretical equations derived by Nobel laureate Kip Thorne to render the black hole 'Gargantua' led to two published peer-reviewed astrophysics research papers.",
    "Christopher Nolan refused to use CGI for the giant dust storms engulfing the Cooper farmhouse. Instead, massive wind machines blew tons of food-grade synthetic dust across the set.",
    "Hans Zimmer composed the iconic organ soundtrack at Temple Church in London on a historic 1926 four-manual organ, recording without ever reading the film's script beforehand.",
  ],
  avengers: [
    "Robert Downey Jr. constantly hid real snacks throughout the Avengers laboratory set. When Tony Stark offers blueberries to Bruce Banner and Steve Rogers, it was completely unscripted.",
    "The line 'I love you 3000' was suggested by Robert Downey Jr. himself, based on something his real-life children would say to him at bedtime.",
    "During the filming of Endgame, Tom Holland was not given a full script because directors Anthony & Joe Russo worried he might accidentally leak major plot points.",
  ],
  oppenheimer: [
    "Christopher Nolan wrote the entire screenplay in the first person ('I walk into the room') so the crew understood every scene was anchored strictly in J. Robert Oppenheimer's subjective view.",
    "To capture the Trinity nuclear test without CGI, the team detonated a blend of gasoline, magnesium, and aluminum powder in the New Mexico desert to create authentic towering fireballs.",
    "The film's 70mm IMAX print is over 11 miles long and weighs roughly 600 pounds, requiring specialized custom platters in projection booths worldwide.",
  ],
  dark_knight: [
    "Heath Ledger locked himself away in a London hotel room for roughly six weeks to develop the Joker's psychotic laugh, posture, and unsettling vocal cadence.",
    "The famous scene where the Joker claps sarcastically in the holding cell following Jim Gordon's promotion was completely improvised by Heath Ledger on the day of filming.",
    "The Dark Knight was the first major Hollywood feature film to partially shoot sequences with 65mm high-resolution IMAX cameras.",
  ],
  inception: [
    "The rotating hallway fight sequence was filmed using a massive 100-foot motorized centrifuge that rotated 360 degrees while Joseph Gordon-Levitt performed his own stunt choreography.",
    "The iconic 'braam' brass blast in Hans Zimmer's score is actually Édith Piaf's song 'Non, je ne regrette rien' slowed down to match the time dilation of the dream levels.",
  ],
  pulp_fiction: [
    "The 1964 Chevelle Malibu driven by Vincent Vega actually belonged to director Quentin Tarantino—and it was stolen during production, only to be recovered by police nearly two decades later.",
    "Quentin Tarantino intentionally never revealed what was inside the glowing briefcase, stating that it represents whatever the viewer desires it to be.",
  ],
  manjummel_boys: [
    "The crew painstakingly reconstructed the treacherous 60-foot deep subterranean Guna Cave inside a massive warehouse in Kochi using fiber and real rock molds to achieve realistic lighting.",
    "The real-life Manjummel Boys group made emotional cameo appearances and consulted closely with director Chidambaram to ensure every detail of the survival ordeal was accurate.",
    "Manjummel Boys became the highest-grossing Malayalam film of all time, crossing over ₹240 crore worldwide.",
  ],
  aavesham: [
    "Fahadh Faasil's character 'Ranga' never physically assaults anyone with his own hands in the first two acts—his reputation and loyal gang handle all confrontations until the climax.",
    "The viral dance sequences and high-energy music tracks composed by Sushin Shyam were recorded with live vintage percussion to create the authentic local Bangalore gangster flavor.",
  ],
  premalu: [
    "Naslen and Mamitha Baiju improvised many of their funniest romantic back-and-forth lines during rehearsals, which director Girish A.D. incorporated into the final shooting script.",
    "Set in Hyderabad, the film became a surprise pan-South blockbuster, grossing over ₹135 crore globally on a modest production budget.",
  ],
  bramayugam: [
    "Director Rahul Sadasivan chose to film entirely in monochrome black-and-white to immerse viewers in 17th-century Malabar folklore and amplify the psychological dread.",
    "Mammootty performed in complete traditional ascetic attire with minimal digital touchups, utilizing theatrical voice projection honed over five decades in cinema.",
  ],
  goat_life: [
    "Prithviraj Sukumaran endured extreme physical transformations over a 16-year production journey, shedding over 30 kilograms to portray Najeeb's desert survival ordeal.",
    "Filmed across the unforgiving deserts of Jordan and Algeria, production was completely stranded for months during global sandstorms and lockdowns.",
  ],
  drishyam: [
    "Jeethu Joseph wrote the original Drishyam script without any violent action scenes, relying entirely on psychological tension and airtight alibi reconstruction.",
    "Drishyam has been officially remade in over six languages, including Chinese ('Sheep Without a Shepherd'), which grossed over $190 million at the international box office.",
  ],
  fight_club: [
    "Director David Fincher confirmed that a Starbucks coffee cup is visible in almost every single scene throughout the movie.",
    "Brad Pitt and Edward Norton took actual soapmaking, boxing, and martial arts classes to prepare for their roles.",
  ],
  matrix: [
    "The iconic green cascading digital rain in The Matrix doesn't contain secret computer code—it was created by scanning symbols from Japanese sushi cookbooks.",
    "Keanu Reeves donated millions of dollars of his backend Matrix royalties to the stunt teams and special effects crew who engineered the revolutionary 'bullet time' rigs.",
  ],
  gladiator: [
    "Russell Crowe was repeatedly injured during the battle sequences, including broken foot bones and cracked hip tendons, but insisted on performing the chariot collisions himself.",
    "The thumbs-up and thumbs-down gestures for gladiatorial combat in Rome were actually the opposite in history, but Ridley Scott kept the modern misconception so audiences wouldn't be confused.",
  ],
  deadpool: [
    "Ryan Reynolds spent over a decade pitching an authentic R-rated Deadpool to studios before leaked test footage generated overwhelming fan demand that forced production to greenlight.",
    "Hugh Jackman came out of Wolverine retirement after realizing his dream was an authentic buddy-comedy dynamic matching the classic 1980s film 'Midnight Run'.",
  ],
}

// Atmospheric cinema loader statuses
export const CINEMA_CALIBRATION_STEPS = [
  "Initializing high-speed media pipeline...",
  "Calibrating 4K cinema stream & dynamic bitrate...",
  "Tuning spatial Dolby Atmos multi-channel audio...",
  "Mounting soft subtitle tracks & video container...",
  "Opening theater doors — starting playback...",
]

// Generic fallback trivia for any film based on cinematic craftsmanship
const GENERIC_TRIVIA_TEMPLATES = [
  "Did you know? Modern cinema sound design utilizes over 64 distinct audio tracks to create a realistic three-dimensional acoustic atmosphere.",
  "Did you know? Directors often shoot scenes at 24 frames per second because it closely replicates the natural motion blur perceived by the human eye.",
  "Did you know? Color grading plays a massive subconscious role in cinema—cool blues heighten tension, while warm ambers evoke memory and nostalgia.",
  "Did you know? High-bitrate HEVC and H.264 streams preserve fine cinematic film grain, ensuring character expressions look razor-sharp on OLED screens.",
  "Did you know? The musical score of a film is typically recorded in a dedicated acoustic scoring stage with an 80-piece live orchestra.",
]

export function getMovieTrivia(title = '', overview = '') {
  const clean = (title || '').toLowerCase()

  // Match against curated trivia
  for (const [key, facts] of Object.entries(CURATED_TRIVIA)) {
    const searchKey = key.replace(/_/g, ' ')
    if (clean.includes(searchKey) || clean.includes(key)) {
      const idx = Math.floor(Math.random() * facts.length)
      return facts[idx]
    }
  }

  // If overview has interesting keywords
  if (overview && overview.length > 50) {
    const sentences = overview.split('. ')
    if (sentences.length > 1) {
      return `Story Hook: "${sentences[0]}." An epic cinematic journey awaits.`
    }
  }

  // Random generic cinema fact
  const fallbackIdx = Math.floor(Math.random() * GENERIC_TRIVIA_TEMPLATES.length)
  return GENERIC_TRIVIA_TEMPLATES[fallbackIdx]
}
